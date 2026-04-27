"""Approval service layer over ApprovalStore.

Centralizes expiry, approval decisions, and dispatch behavior so CLI handlers can
remain thin wrappers.
"""
from dataclasses import dataclass
import time
from typing import Any
import uuid

from .approval import ApprovalStore, ApprovalEnvelope
from .audit import AuditLog
from .config import Config
from .logging_util import get_logger
from .notifier import build_notifier
from .tools.message_send import dispatch_message_send
from .tools.call_phone import dispatch_call_phone
from .tools.install_app import dispatch_install_app
from .tools.uninstall_app import dispatch_uninstall_app
from .tools.payments import dispatch_payment
from .tools.trade import dispatch_trade

logger = get_logger("approval_service")


_TIER_DISPATCH_COOLDOWN_SECONDS: dict[str, int] = {
    "low": 0,
    "medium": 0,
    "high": 5,
    "critical": 5,
}


@dataclass
class DispatchSummary:
    failures: int
    items: list[dict[str, Any]]
    remaining: int
    skipped_by_kind_cooldown: int
    skipped_by_tier_cooldown: int = 0
    skipped_reason: str = ""


class ApprovalService:
    def __init__(self, config: Config):
        self.config = config
        self.store = ApprovalStore(config.approval_db)
        self.audit = AuditLog(config.audit_db)
        self._notifier = build_notifier(
            channel=config.approval_channel,
            ntfy_topic=config.ntfy_topic,
            ntfy_url=config.ntfy_url,
            ntfy_priority=config.ntfy_priority,
            ntfy_token=config.get_secret("JARVIS_NTFY_TOKEN") or config.ntfy_token,
        )

    def _expire_pending(self) -> None:
        expired_ids = self.store.expire_pending_ids(self.config.approvals_ttl_seconds)
        for approval_id in expired_ids:
            row = self.store.get(approval_id)
            self.audit.append(
                "approval_expired",
                {
                    "approval_id": approval_id,
                    "reason": "expired: ttl exceeded",
                    "correlation_id": row["correlation_id"] if row else "",
                },
            )

    def request(
        self,
        kind: str,
        payload: dict[str, Any],
        correlation_id: str | None = None,
        envelope: "ApprovalEnvelope | None" = None,
    ) -> str:
        correlation_id = correlation_id or str(uuid.uuid4())
        env = envelope or ApprovalEnvelope()
        approval_id = self.store.request(
            kind=kind,
            payload=payload,
            correlation_id=correlation_id,
            envelope=env,
        )
        logger.info(
            f"Approval requested: {approval_id} "
            f"(kind={kind}, risk_tier={env.risk_tier}, correlation_id={correlation_id})"
        )
        self.audit.append(
            "approval_requested",
            {
                "approval_id": approval_id,
                "correlation_id": correlation_id,
                "kind": kind,
                "payload": payload,
                **env.to_dict(),
            },
        )
        try:
            notify_result = self._notifier.notify(approval_id, kind, payload, envelope=env)
            if not notify_result.get("sent"):
                logger.debug("push notification not sent: %s", notify_result)
        except Exception as exc:  # noqa: BLE001
            logger.warning("notifier raised unexpectedly: %s", exc)
        return approval_id

    def list_pending(self, limit: int = 100) -> list[dict[str, Any]]:
        self._expire_pending()
        return self.store.list_pending(limit=limit)

    def approve(self, approval_id: str, reason: str = "") -> bool:
        self._expire_pending()
        ok = self.store.approve(approval_id, reason=reason)
        if ok:
            row = self.store.get(approval_id)
            logger.info(f"Approval approved: {approval_id} (reason={reason or 'none'})")
            self.audit.append(
                "approval_approved",
                {
                    "approval_id": approval_id,
                    "reason": reason,
                    "correlation_id": row["correlation_id"] if row else "",
                },
            )
        else:
            logger.warning(f"Approval not found or not pending: {approval_id}")
        return ok

    def reject(self, approval_id: str, reason: str = "") -> bool:
        self._expire_pending()
        ok = self.store.reject(approval_id, reason=reason)
        if ok:
            row = self.store.get(approval_id)
            logger.info(f"Approval rejected: {approval_id} (reason={reason or 'none'})")
            self.audit.append(
                "approval_rejected",
                {
                    "approval_id": approval_id,
                    "reason": reason,
                    "correlation_id": row["correlation_id"] if row else "",
                },
            )
        else:
            logger.warning(f"Approval not found or not pending: {approval_id}")
        return ok

    def edit(
        self,
        approval_id: str,
        payload: dict[str, Any] | None = None,
        envelope: "ApprovalEnvelope | None" = None,
    ) -> bool:
        """Edit a pending approval's payload/envelope metadata."""
        self._expire_pending()
        row = self.store.get(approval_id)
        if not row or row["status"] != "pending":
            logger.warning(f"Approval not found or not pending: {approval_id}")
            return False

        next_payload = payload if payload is not None else row["payload"]
        next_env = envelope or ApprovalEnvelope.from_dict(
            {
                "action": row.get("action", ""),
                "reason": row.get("reason", ""),
                "budget_impact": row.get("budget_impact", 0.0),
                "ttl_seconds": row.get("ttl_seconds", 0),
                "risk_tier": row.get("risk_tier", "medium"),
            }
        )

        ok = self.store.edit_pending(
            approval_id=approval_id,
            payload=next_payload,
            envelope=next_env,
        )
        if ok:
            logger.info(f"Approval edited: {approval_id}")
            self.audit.append(
                "approval_edited",
                {
                    "approval_id": approval_id,
                    "correlation_id": row.get("correlation_id", ""),
                    "payload": next_payload,
                    **next_env.to_dict(),
                },
            )
        else:
            logger.warning(f"Approval not found or not pending: {approval_id}")
        return ok

    def dispatch(self, limit: int = 100) -> DispatchSummary:
        self._expire_pending()

        if self.config.approvals_dispatch_max_per_run <= 0:
            return DispatchSummary(
                failures=0,
                items=[],
                remaining=0,
                skipped_by_kind_cooldown=0,
                skipped_by_tier_cooldown=0,
                skipped_reason="max_per_run_zero",
            )

        last_dispatch_ts = self.store.last_dispatch_ts()
        if (
            self.config.approvals_dispatch_cooldown_seconds > 0
            and last_dispatch_ts is not None
            and time.time() - last_dispatch_ts
            < self.config.approvals_dispatch_cooldown_seconds
        ):
            return DispatchSummary(
                failures=0,
                items=[],
                remaining=0,
                skipped_by_kind_cooldown=0,
                skipped_by_tier_cooldown=0,
                skipped_reason="global_cooldown",
            )

        approved = self.store.list_approved(limit=limit)
        if not approved:
            return DispatchSummary(
                failures=0,
                items=[],
                remaining=0,
                skipped_by_kind_cooldown=0,
                skipped_by_tier_cooldown=0,
                skipped_reason="none_approved",
            )

        now = time.time()
        dispatchable: list[dict[str, Any]] = []
        skipped_by_kind_cooldown = 0
        skipped_by_tier_cooldown = 0
        for row in approved:
            kind = row["kind"]
            kind_cooldown = self.config.approvals_dispatch_cooldown_by_kind.get(kind, 0)
            if kind_cooldown > 0:
                last_kind_dispatch = self.store.last_dispatch_ts_for_kind(kind)
                if (
                    last_kind_dispatch is not None
                    and now - last_kind_dispatch < kind_cooldown
                ):
                    skipped_by_kind_cooldown += 1
                    continue

            risk_tier = str(row.get("risk_tier", "medium") or "medium").strip().lower()
            tier_cooldown = _TIER_DISPATCH_COOLDOWN_SECONDS.get(risk_tier, 0)
            decision_ts = row.get("decision_ts")
            if tier_cooldown > 0 and isinstance(decision_ts, (int, float)):
                if now - float(decision_ts) < tier_cooldown:
                    skipped_by_tier_cooldown += 1
                    continue
            dispatchable.append(row)

        if not dispatchable:
            if skipped_by_kind_cooldown > 0 and skipped_by_tier_cooldown > 0:
                skipped_reason = "kind_or_tier_cooldown"
            elif skipped_by_kind_cooldown > 0:
                skipped_reason = "kind_cooldown"
            else:
                skipped_reason = "tier_cooldown"
            return DispatchSummary(
                failures=0,
                items=[],
                remaining=0,
                skipped_by_kind_cooldown=skipped_by_kind_cooldown,
                skipped_by_tier_cooldown=skipped_by_tier_cooldown,
                skipped_reason=skipped_reason,
            )

        failures = 0
        dispatched_items = []
        for row in dispatchable[: self.config.approvals_dispatch_max_per_run]:
            if row["kind"] == "message_send":
                result = dispatch_message_send(
                    mode=self.config.message_send_mode,
                    outbox_path=self.config.message_outbox,
                    payload=row["payload"],
                )
                success = result.get("status") == "dry_run_sent"
            elif row["kind"] == "call_phone":
                result = dispatch_call_phone(
                    mode=self.config.call_phone_mode,
                    calls_log_path=self.config.calls_log_path,
                    payload=row["payload"],
                    provider=self.config.telephony_provider,
                    caller_id=self.config.telephony_caller_id,
                    twilio_account_sid=self.config.get_secret("TWILIO_ACCOUNT_SID"),
                    twilio_auth_token=self.config.get_secret("TWILIO_AUTH_TOKEN"),
                )
                success = result.get("status") in {
                    "dry_run_logged",
                    "twilio_queued",
                    "human_handoff_requested",
                }
            elif row["kind"] == "payments":
                result = dispatch_payment(
                    mode=self.config.payments_mode,
                    ledger_path=self.config.payments_ledger,
                    payload=row["payload"],
                    tx_limit=self.config.payments_tx_limit,
                    monthly_cap=self.config.payments_monthly_cap,
                    allowed_mccs=self.config.payments_allowed_mccs,
                    budget_db_path=self.config.payments_budget_db,
                )
                success = result.get("status") == "dry_run_logged"
            elif row["kind"] == "trade":
                result = dispatch_trade(
                    mode=self.config.trades_mode,
                    trades_log_path=self.config.trades_log,
                    payload=row["payload"],
                    paper_broker=self.config.trading_paper_broker,
                    alpaca_api_key=(
                        self.config.get_secret("ALPACA_API_KEY")
                        or self.config.get_secret("ALPACA_API_KEY_ID")
                    ),
                    alpaca_api_secret=(
                        self.config.get_secret("ALPACA_API_SECRET")
                        or self.config.get_secret("ALPACA_API_SECRET_KEY")
                    ),
                    account_equity=self.config.trading_account_equity,
                    max_position_pct=self.config.trading_max_position_pct,
                    live_cooldown_seconds=self.config.trading_live_cooldown_seconds,
                    max_daily_drawdown_pct=self.config.trading_daily_drawdown_kill_pct,
                )
                success = result.get("status") in {"dry_run_logged", "paper_submitted", "live_submitted"}
            elif row["kind"] == "install_app":
                result = dispatch_install_app(payload=row["payload"])
                success = bool(result.get("ok")) and result.get("status") in {
                    "installed_with_brew",
                    "opened_download_url",
                }
            elif row["kind"] == "uninstall_app":
                result = dispatch_uninstall_app(mode="live", payload=row["payload"])
                success = result.get("status") in {"uninstalled", "manual_removal_needed"}
            else:
                result = {"error": f"no dispatcher for kind '{row['kind']}'"}
                success = False

            self.store.mark_dispatched(row["id"], success=success, result=result)
            self.audit.append(
                "approval_dispatched",
                {
                    "approval_id": row["id"],
                    "kind": row["kind"],
                    "correlation_id": row.get("correlation_id", ""),
                    "success": success,
                    "result": result,
                },
            )
            dispatched_items.append({"id": row["id"], "result": result})
            if not success:
                failures += 1

        remaining = len(dispatchable) - min(
            len(dispatchable),
            self.config.approvals_dispatch_max_per_run,
        )

        return DispatchSummary(
            failures=failures,
            items=dispatched_items,
            remaining=remaining,
            skipped_by_kind_cooldown=skipped_by_kind_cooldown,
            skipped_by_tier_cooldown=skipped_by_tier_cooldown,
        )
