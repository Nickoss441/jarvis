"""Approval-gated payments tool."""
import json
from datetime import datetime, timezone
from pathlib import Path
from dataclasses import dataclass

from jarvis.tools import Tool
from jarvis.payments_ledger import PaymentsBudgetLedger, month_key_for


@dataclass
class PaymentResult:
    """Result from a payment dispatch."""

    status: str
    transaction_id: str | None = None
    amount: float | None = None
    error: str | None = None


def spend_tier_for_amount(amount: float) -> str:
    """Map amount to configured spend tiers.

    Tiers:
    - 0-10   (inclusive of 10)
    - 10-100 (greater than 10 up to and including 100)
    - 100+   (greater than 100)
    """
    if amount <= 10:
        return "0-10"
    if amount <= 100:
        return "10-100"
    return "100+"


def risk_tier_for_spend_tier(spend_tier: str) -> str:
    mapping = {
        "0-10": "low",
        "10-100": "medium",
        "100+": "high",
    }
    return mapping.get(spend_tier, "medium")


def build_payment_proposal(
    *,
    amount: float,
    currency: str,
    recipient: str,
    reason: str = "",
    merchant: str = "",
    line_items: list[dict] | None = None,
) -> dict:
    """Build and validate a payment proposal payload.

    Line item schema:
    - description: non-empty string
    - quantity: positive number
    - unit_price: positive number

    If line_items are present, their computed total must match ``amount``
    within a 1-cent tolerance.
    """
    merchant_norm = (merchant or "").strip()
    items = line_items or []

    if items and not merchant_norm:
        return {"error": "merchant is required when line_items are provided"}

    normalized_items: list[dict] = []
    items_total = 0.0

    for idx, raw in enumerate(items):
        if not isinstance(raw, dict):
            return {"error": f"line_items[{idx}] must be an object"}

        description = str(raw.get("description") or "").strip()
        quantity = raw.get("quantity")
        unit_price = raw.get("unit_price")

        if not description:
            return {"error": f"line_items[{idx}].description must be non-empty"}
        if not isinstance(quantity, (int, float)) or quantity <= 0:
            return {"error": f"line_items[{idx}].quantity must be positive"}
        if not isinstance(unit_price, (int, float)) or unit_price <= 0:
            return {"error": f"line_items[{idx}].unit_price must be positive"}

        line_total = float(quantity) * float(unit_price)
        items_total += line_total
        normalized_items.append(
            {
                "description": description,
                "quantity": float(quantity),
                "unit_price": float(unit_price),
                "line_total": round(line_total, 2),
            }
        )

    if normalized_items and abs(items_total - float(amount)) > 0.01:
        return {
            "error": (
                "amount does not match line_items total "
                f"({float(amount):.2f} != {items_total:.2f})"
            )
        }

    return {
        "amount": float(amount),
        "currency": str(currency).upper(),
        "recipient": str(recipient),
        "reason": str(reason),
        "merchant": merchant_norm,
        "line_items": normalized_items,
        "proposal_total": round(items_total if normalized_items else float(amount), 2),
    }


def dispatch_payment(
    mode: str,
    ledger_path: Path | str,
    payload: dict,
    tx_limit: float = 10000.0,
    monthly_cap: float = 10000.0,
    allowed_mccs: tuple[str, ...] | list[str] | None = None,
    budget_db_path: Path | str | None = None,
) -> dict:
    """Dispatch a payment in given mode (dry_run or live).

    Args:
        mode: "dry_run" or "live"
        ledger_path: Path to JSONL file for dry_run logs
        payload: Payment details (amount, currency, recipient, reason)

    Returns:
        dict with status and transaction_id or error
    """
    ledger_path = Path(ledger_path)

    # Validate required fields
    if "amount" not in payload:
        return {"error": "Missing required field: amount"}
    if "currency" not in payload:
        return {"error": "Missing required field: currency"}
    if "recipient" not in payload:
        return {"error": "Missing required field: recipient"}

    amount = payload.get("amount")
    currency = payload.get("currency", "USD")

    # Validate amount
    if not isinstance(amount, (int, float)) or amount <= 0:
        return {"error": "amount must be positive number"}

    # Per-transaction virtual-card limit
    if not isinstance(tx_limit, (int, float)) or tx_limit <= 0:
        return {"error": "invalid tx_limit configuration"}
    if amount > float(tx_limit):
        return {"error": f"amount {amount} exceeds tx_limit of {float(tx_limit)}"}

    # Validate currency (basic check)
    if not isinstance(currency, str) or len(currency) != 3:
        return {"error": "currency must be 3-letter code (e.g., USD, EUR)"}

    # Optional merchant category allowlist (MCC)
    mcc = str(payload.get("mcc") or "").strip()
    allowlist = {
        str(code).strip()
        for code in (allowed_mccs or [])
        if str(code).strip()
    }
    if allowlist:
        if not mcc:
            return {"error": "mcc is required when allowed_mccs policy is configured"}
        if mcc not in allowlist:
            return {"error": f"mcc '{mcc}' is not allowed by policy"}

    # Optional monthly cap (current UTC month, per-currency)
    if not isinstance(monthly_cap, (int, float)) or monthly_cap <= 0:
        return {"error": "invalid monthly_cap configuration"}

    now = datetime.now(timezone.utc)
    currency_up = str(currency).upper()
    db_path = Path(budget_db_path) if budget_db_path else ledger_path.with_suffix(".budget.db")
    budget_ledger = PaymentsBudgetLedger(db_path)
    month_key = month_key_for(now)
    effective_cap = budget_ledger.effective_month_cap(month_key, currency_up, float(monthly_cap))
    monthly_total = budget_ledger.monthly_spend(month_key, currency_up)

    projected_total = monthly_total + float(amount)
    if projected_total > effective_cap:
        return {
            "error": (
                f"monthly cap exceeded for {currency_up}: "
                f"{projected_total:.2f} > {effective_cap:.2f}"
            )
        }

    if mode == "dry_run":
        import uuid

        txid = str(payload.get("external_txid") or "").strip() or str(uuid.uuid4())
        entry = {
            "ts": now.isoformat(),
            "txid": txid,
            "amount": amount,
            "currency": currency_up,
            "recipient": payload.get("recipient"),
            "reason": payload.get("reason", ""),
            "mcc": mcc,
            "mode": "dry_run",
        }

        ledger_path.parent.mkdir(parents=True, exist_ok=True)
        with open(ledger_path, "a") as f:
            f.write(json.dumps(entry) + "\n")

        budget_ledger.record_transaction(
            ts=now,
            currency=currency_up,
            amount=float(amount),
            recipient=str(payload.get("recipient") or ""),
            reason=str(payload.get("reason") or ""),
            mcc=mcc,
            external_txid=txid,
            monthly_cap=float(monthly_cap),
        )

        return {
            "status": "dry_run_logged",
            "txid": txid,
            "amount": amount,
            "currency": currency_up,
        }
    else:
        return {"error": f"Unsupported mode: {mode}"}


def make_payments_tool(
    request_approval=None,
    get_approval=None,
) -> Tool:
    """Create payments tool with approval gating.

    Args:
        request_approval: Function(kind, payload) -> approval_id
        get_approval: Function(approval_id) -> approval dict

    Returns:
        Tool instance for payments
    """

    def handler(
        amount: float,
        currency: str,
        recipient: str,
        reason: str = "",
        mcc: str = "",
        merchant: str = "",
        line_items: list[dict] | None = None,
    ) -> dict:
        """Handle payment request.

        Args:
            amount: Payment amount (max 10000)
            currency: 3-letter currency code (USD, EUR, etc.)
            recipient: Recipient identifier (email, address, account)
            reason: Payment reason/memo

        Returns:
            dict with status and correlation_id or error
        """
        if amount <= 0:
            return {"error": "amount must be positive"}
        if amount > 10000:
            return {"error": f"amount {amount} exceeds budget cap of 10000"}

        proposal = build_payment_proposal(
            amount=amount,
            currency=currency,
            recipient=recipient,
            reason=reason,
            merchant=merchant,
            line_items=line_items,
        )
        if "error" in proposal:
            return proposal

        spend_tier = spend_tier_for_amount(float(amount))
        risk_tier = risk_tier_for_spend_tier(spend_tier)

        payload = {
            **proposal,
            "mcc": (mcc or "").strip(),
            "spend_tier": spend_tier,
        }

        if not request_approval:
            return {"error": "approval gating not configured"}

        # Backward-compatible call: newer request_approval call-sites accept
        # envelope metadata, older mocks/utilities may only accept kind+payload.
        try:
            from jarvis.approval import ApprovalEnvelope

            envelope = ApprovalEnvelope(
                action="execute_payment",
                reason=(reason or "payment request").strip(),
                budget_impact=float(amount),
                risk_tier=risk_tier,
            )
            approval_id = request_approval("payments", payload, envelope=envelope)
        except TypeError:
            approval_id = request_approval("payments", payload)
        approval = get_approval(approval_id) if get_approval else None

        return {
            "status": "pending_approval",
            "kind": "payments",
            "approval_id": approval_id,
            "correlation_id": approval.get("correlation_id") if approval else None,
            "amount": amount,
            "currency": currency,
            "spend_tier": spend_tier,
        }

    return Tool(
        name="payments",
        description="Send a payment (approval-required). Must be approved via approvals queue.",
        input_schema={
            "type": "object",
            "properties": {
                "amount": {
                    "type": "number",
                    "description": "Payment amount (max 10000 per transaction)",
                },
                "currency": {
                    "type": "string",
                    "description": "3-letter currency code (USD, EUR, GBP, etc.)",
                },
                "recipient": {
                    "type": "string",
                    "description": "Recipient identifier (email, wallet address, account ID, etc.)",
                },
                "reason": {
                    "type": "string",
                    "description": "Payment reason/memo (optional)",
                },
                "mcc": {
                    "type": "string",
                    "description": "Optional merchant category code (MCC)",
                },
                "merchant": {
                    "type": "string",
                    "description": "Merchant name for proposal and reconciliation context",
                },
                "line_items": {
                    "type": "array",
                    "description": "Optional line-item breakdown used for proposal validation",
                    "items": {
                        "type": "object",
                        "properties": {
                            "description": {"type": "string"},
                            "quantity": {"type": "number"},
                            "unit_price": {"type": "number"},
                        },
                    },
                },
            },
        },
        handler=handler,
        tier="gated",
    )
