"""Approval-gated trade tool."""
import datetime as dt
import json
from pathlib import Path
from dataclasses import dataclass
import time
from typing import Any, Callable
import uuid

from jarvis.audit import AuditLog
from jarvis.tools import Tool

try:
    import httpx as httpx  # noqa: PLC0414
except ImportError:
    httpx = None  # type: ignore[assignment]


@dataclass
class TradeResult:
    """Result from a trade dispatch."""

    status: str
    order_id: str | None = None
    instrument: str | None = None
    side: str | None = None
    size: float | None = None
    error: str | None = None


def _latest_trade_timestamp(trades_log_path: Path | str, mode: str) -> float | None:
    path = Path(trades_log_path)
    if not path.exists():
        return None

    latest: float | None = None
    with path.open(encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if str(payload.get("mode") or "").strip().lower() != mode:
                continue
            ts = payload.get("ts")
            if isinstance(ts, (int, float)):
                latest = max(float(ts), latest or float(ts))
    return latest


def daily_drawdown_limit_for_equity(account_equity: float, max_daily_drawdown_pct: float) -> float:
    return float(account_equity) * (float(max_daily_drawdown_pct) / 100.0)


def current_daily_realized_pnl(
    trades_log_path: Path | str,
    *,
    mode: str = "live",
    now: dt.datetime | None = None,
) -> float:
    path = Path(trades_log_path)
    if not path.exists():
        return 0.0

    current_day = (now or dt.datetime.now(dt.timezone.utc)).date()
    total = 0.0
    with path.open(encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if str(payload.get("mode") or "").strip().lower() != mode:
                continue
            ts = payload.get("ts")
            if not isinstance(ts, (int, float)):
                continue
            event_day = dt.datetime.fromtimestamp(float(ts), tz=dt.timezone.utc).date()
            if event_day != current_day:
                continue
            pnl_delta = payload.get("pnl_delta", 0.0)
            if isinstance(pnl_delta, (int, float)):
                total += float(pnl_delta)
    return total


def validate_daily_drawdown_pause(
    *,
    trades_log_path: Path | str,
    account_equity: float,
    max_daily_drawdown_pct: float,
    now: dt.datetime | None = None,
) -> str | None:
    if account_equity <= 0 or max_daily_drawdown_pct <= 0:
        return None
    drawdown_limit = daily_drawdown_limit_for_equity(account_equity, max_daily_drawdown_pct)
    pnl_total = current_daily_realized_pnl(trades_log_path, mode="live", now=now)
    if pnl_total <= -drawdown_limit:
        return (
            f"daily drawdown pause active: realized PnL {pnl_total:.2f} breached "
            f"-{drawdown_limit:.2f} ({float(max_daily_drawdown_pct):.2f}% of equity {float(account_equity):.2f})"
        )
    return None


def position_size_cap_for_equity(account_equity: float, max_position_pct: float) -> float:
    return float(account_equity) * (float(max_position_pct) / 100.0)


def validate_position_size_cap(
    *,
    size: float,
    account_equity: float,
    max_position_pct: float,
) -> str | None:
    if account_equity <= 0 or max_position_pct <= 0:
        return None
    max_size = position_size_cap_for_equity(account_equity, max_position_pct)
    if float(size) > max_size:
        return (
            f"size {float(size)} exceeds max position size of {max_size:.2f} "
            f"({float(max_position_pct):.2f}% of equity {float(account_equity):.2f})"
        )
    return None


def build_trade_proposal(
    *,
    instrument: str,
    side: str,
    size: float,
    rationale: str = "",
    stop_loss: float | None = None,
    take_profit: float | None = None,
) -> dict:
    """Build and validate a normalized trade proposal payload."""
    instrument_norm = str(instrument or "").strip().upper()
    side_norm = str(side or "").strip().lower()
    rationale_norm = str(rationale or "").strip()

    if not instrument_norm:
        return {"error": "instrument must be non-empty (e.g., AAPL, BTC/USD)"}
    if side_norm not in ("buy", "sell"):
        return {"error": "side must be 'buy' or 'sell'"}
    if not isinstance(size, (int, float)) or float(size) <= 0:
        return {"error": "size must be positive number"}
    if not rationale_norm:
        return {"error": "rationale is required"}

    normalized_stop_loss: float | None = None
    normalized_take_profit: float | None = None

    if stop_loss is not None:
        if not isinstance(stop_loss, (int, float)) or float(stop_loss) <= 0:
            return {"error": "stop_loss must be positive number when provided"}
        normalized_stop_loss = float(stop_loss)

    if take_profit is not None:
        if not isinstance(take_profit, (int, float)) or float(take_profit) <= 0:
            return {"error": "take_profit must be positive number when provided"}
        normalized_take_profit = float(take_profit)

    if normalized_stop_loss is not None and normalized_take_profit is not None:
        if side_norm == "buy" and normalized_stop_loss >= normalized_take_profit:
            return {"error": "buy trades require stop_loss below take_profit"}
        if side_norm == "sell" and normalized_stop_loss <= normalized_take_profit:
            return {"error": "sell trades require stop_loss above take_profit"}

    return {
        "instrument": instrument_norm,
        "side": side_norm,
        "size": float(size),
        "rationale": rationale_norm,
        "stop_loss": normalized_stop_loss,
        "take_profit": normalized_take_profit,
    }


def build_trade_replay_report(audit_log: AuditLog, limit: int = 50) -> dict[str, Any]:
    safe_limit = max(1, min(int(limit), 500))
    request_rows = audit_log.recent(limit=max(50, safe_limit * 5), kind="approval_requested")

    trade_requests: list[dict[str, Any]] = []
    for row in request_rows:
        payload = row.get("payload", {})
        if payload.get("kind") != "trade":
            continue
        trade_requests.append(row)
        if len(trade_requests) >= safe_limit:
            break

    trades: list[dict[str, Any]] = []
    status_counts: dict[str, int] = {}
    mode_counts: dict[str, int] = {}
    success_count = 0
    failure_count = 0

    for request in trade_requests:
        request_payload = request.get("payload", {})
        proposal = request_payload.get("payload", {})
        correlation_id = str(request_payload.get("correlation_id") or "")
        audit_rows = audit_log.by_correlation_id(correlation_id, limit=20) if correlation_id else []

        approved = next((row for row in audit_rows if row["kind"] == "approval_approved"), None)
        rejected = next((row for row in audit_rows if row["kind"] == "approval_rejected"), None)
        dispatched = next((row for row in audit_rows if row["kind"] == "approval_dispatched"), None)

        dispatch_payload = dispatched["payload"] if dispatched else {}
        result = dispatch_payload.get("result", {}) if dispatched else {}
        success = bool(dispatch_payload.get("success")) if dispatched else False
        mode = str(result.get("status") or proposal.get("mode") or "unknown")

        if dispatched:
            status = str(result.get("status") or ("dispatch_failed" if not success else "dispatched"))
        elif rejected:
            status = "rejected"
        elif approved:
            status = "approved_pending_dispatch"
        else:
            status = "pending_approval"

        status_counts[status] = status_counts.get(status, 0) + 1
        mode_counts[mode] = mode_counts.get(mode, 0) + 1
        if dispatched and success:
            success_count += 1
        elif dispatched and not success:
            failure_count += 1

        trades.append(
            {
                "approval_id": request_payload.get("approval_id"),
                "correlation_id": correlation_id,
                "requested_ts": request.get("ts"),
                "approved_ts": approved.get("ts") if approved else None,
                "rejected_ts": rejected.get("ts") if rejected else None,
                "dispatched_ts": dispatched.get("ts") if dispatched else None,
                "status": status,
                "success": success if dispatched else None,
                "instrument": proposal.get("instrument"),
                "side": proposal.get("side"),
                "size": proposal.get("size"),
                "rationale": proposal.get("rationale") or proposal.get("reason"),
                "stop_loss": proposal.get("stop_loss"),
                "take_profit": proposal.get("take_profit"),
                "live_confirm": bool(proposal.get("live_confirm")),
                "dispatch_result": result if dispatched else None,
            }
        )

    return {
        "ok": True,
        "count": len(trades),
        "success_count": success_count,
        "failure_count": failure_count,
        "status_counts": status_counts,
        "mode_counts": mode_counts,
        "trades": trades,
    }


def build_trade_performance_report(
    trades_log_path: Path | str,
    *,
    audit_log: AuditLog | None = None,
    mode: str = "paper",
    min_trading_days: int = 20,
    min_trades: int = 100,
    latency_anomaly_ms: float = 1000.0,
    slippage_anomaly_bps: float = 50.0,
    audit_scan_limit: int = 5000,
) -> dict[str, Any]:
    path = Path(trades_log_path)
    if mode not in {"dry_run", "paper", "live"}:
        raise ValueError(f"unsupported mode: {mode}")

    def _maybe_float(value: Any) -> float | None:
        if isinstance(value, (int, float)):
            return float(value)
        return None

    entries: list[dict[str, Any]] = []
    if path.exists():
        with path.open(encoding="utf-8") as handle:
            for raw_line in handle:
                line = raw_line.strip()
                if not line:
                    continue
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if str(payload.get("mode") or "").strip().lower() != mode:
                    continue
                entries.append(payload)

    sorted_entries = sorted(entries, key=lambda entry: _maybe_float(entry.get("ts")) or 0.0)
    first_ts = _maybe_float(sorted_entries[0].get("ts")) if sorted_entries else None
    last_ts = _maybe_float(sorted_entries[-1].get("ts")) if sorted_entries else None
    trading_days: set[str] = set()
    pnl_values: list[float] = []
    cumulative_pnl = 0.0
    equity_curve: list[float] = []
    latency_anomaly_count = 0
    slippage_anomaly_count = 0

    for entry in sorted_entries:
        ts = _maybe_float(entry.get("ts"))
        if ts is not None:
            trading_days.add(dt.datetime.fromtimestamp(ts, tz=dt.timezone.utc).date().isoformat())

        pnl_delta = _maybe_float(entry.get("pnl_delta")) or 0.0
        pnl_values.append(pnl_delta)
        cumulative_pnl += pnl_delta
        equity_curve.append(cumulative_pnl)

        latency_ms = _maybe_float(entry.get("latency_ms"))
        if latency_ms is not None and latency_ms > latency_anomaly_ms:
            latency_anomaly_count += 1

        slippage_bps = _maybe_float(entry.get("slippage_bps"))
        if slippage_bps is not None and abs(slippage_bps) > slippage_anomaly_bps:
            slippage_anomaly_count += 1

    gross_profit = sum(value for value in pnl_values if value > 0)
    gross_loss = abs(sum(value for value in pnl_values if value < 0))
    net_pnl = sum(pnl_values)
    wins = [value for value in pnl_values if value > 0]
    losses = [value for value in pnl_values if value < 0]

    peak = 0.0
    max_drawdown = 0.0
    for point in equity_curve:
        peak = max(peak, point)
        max_drawdown = max(max_drawdown, peak - point)

    policy_violation_count = 0
    dispatch_failure_count = 0
    if audit_log is not None:
        for row in audit_log.recent(limit=max(1, audit_scan_limit)):
            payload = row.get("payload", {})
            if row.get("kind") == "tool_call" and payload.get("name") == "trade":
                policy = payload.get("policy", {})
                if isinstance(policy, dict) and policy.get("allowed") is False:
                    policy_violation_count += 1
            if row.get("kind") == "approval_dispatched" and payload.get("kind") == "trade":
                if not bool(payload.get("success")):
                    dispatch_failure_count += 1

    trade_count = len(sorted_entries)
    trading_day_count = len(trading_days)

    return {
        "ok": True,
        "mode": mode,
        "trades_log": str(path),
        "window": {
            "start_ts": first_ts,
            "end_ts": last_ts,
            "start": dt.datetime.fromtimestamp(first_ts, tz=dt.timezone.utc).isoformat() if first_ts is not None else None,
            "end": dt.datetime.fromtimestamp(last_ts, tz=dt.timezone.utc).isoformat() if last_ts is not None else None,
        },
        "trade_count": trade_count,
        "trading_days": trading_day_count,
        "minimum_window": {
            "trading_days": min_trading_days,
            "trades": min_trades,
        },
        "meets_minimum_window": trading_day_count >= min_trading_days and trade_count >= min_trades,
        "pnl": {
            "gross_profit": gross_profit,
            "gross_loss": gross_loss,
            "net": net_pnl,
            "average_per_trade": (net_pnl / trade_count) if trade_count else 0.0,
            "average_win": (sum(wins) / len(wins)) if wins else None,
            "average_loss": (sum(losses) / len(losses)) if losses else None,
            "profit_factor": (gross_profit / gross_loss) if gross_loss > 0 else None,
            "win_rate": (len(wins) / trade_count) if trade_count else 0.0,
        },
        "risk": {
            "max_drawdown": max_drawdown,
        },
        "anomalies": {
            "latency_count": latency_anomaly_count,
            "slippage_count": slippage_anomaly_count,
            "latency_threshold_ms": latency_anomaly_ms,
            "slippage_threshold_bps": slippage_anomaly_bps,
        },
        "audit": {
            "policy_violation_count": policy_violation_count,
            "dispatch_failure_count": dispatch_failure_count,
        },
    }


def dispatch_trade(
    mode: str,
    trades_log_path: Path | str,
    payload: dict,
    paper_broker: str = "alpaca",
    alpaca_api_key: str = "",
    alpaca_api_secret: str = "",
    account_equity: float = 100000.0,
    max_position_pct: float = 2.0,
    live_cooldown_seconds: int = 300,
    max_daily_drawdown_pct: float = 5.0,
) -> dict:
    """Dispatch a trade order in given mode (dry_run or paper).

    Args:
        mode: "dry_run" or "paper"
        trades_log_path: Path to JSONL file for trade logs
        payload: Trade details (instrument, side, size, reason)

    Returns:
        dict with status and order_id or error
    """
    trades_log_path = Path(trades_log_path)

    # Validate required fields
    if "instrument" not in payload:
        return {"error": "Missing required field: instrument"}
    if "side" not in payload:
        return {"error": "Missing required field: side"}
    if "size" not in payload:
        return {"error": "Missing required field: size"}

    proposal = build_trade_proposal(
        instrument=str(payload.get("instrument") or ""),
        side=str(payload.get("side") or ""),
        size=payload.get("size"),
        rationale=str(payload.get("rationale") or payload.get("reason") or ""),
        stop_loss=payload.get("stop_loss"),
        take_profit=payload.get("take_profit"),
    )
    if "error" in proposal:
        return proposal

    instrument = proposal["instrument"]
    side = proposal["side"]
    size = proposal["size"]
    rationale = proposal["rationale"]
    stop_loss = proposal["stop_loss"]
    take_profit = proposal["take_profit"]

    if size > 10000:  # Position size cap
        return {"error": f"size {size} exceeds position cap of 10000"}

    cap_error = validate_position_size_cap(
        size=size,
        account_equity=account_equity,
        max_position_pct=max_position_pct,
    )
    if cap_error:
        return {"error": cap_error}

    now_ts = time.time()

    if mode == "dry_run":
        order_id = str(uuid.uuid4())[:8]
        entry = {
            "ts": now_ts,
            "order_id": order_id,
            "instrument": instrument,
            "side": side,
            "size": size,
            "rationale": rationale,
            "reason": rationale,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "mode": "dry_run",
        }

        trades_log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(trades_log_path, "a") as f:
            f.write(json.dumps(entry) + "\n")

        return {
            "status": "dry_run_logged",
            "order_id": order_id,
            "instrument": instrument,
            "side": side,
            "size": size,
            "rationale": rationale,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
        }

    if mode == "live":
        drawdown_error = validate_daily_drawdown_pause(
            trades_log_path=trades_log_path,
            account_equity=account_equity,
            max_daily_drawdown_pct=max_daily_drawdown_pct,
        )
        if drawdown_error:
            return {"error": drawdown_error}

        if not bool(payload.get("live_confirm")):
            return {"error": "live mode requires per-trade confirm (set live_confirm=true)"}

        latest_live_ts = _latest_trade_timestamp(trades_log_path, "live")
        if (
            latest_live_ts is not None
            and live_cooldown_seconds > 0
            and now_ts - latest_live_ts < live_cooldown_seconds
        ):
            remaining = int(live_cooldown_seconds - (now_ts - latest_live_ts))
            return {"error": f"live trade cooldown active: wait {remaining}s before next live trade"}

    elif mode != "paper":
        return {"error": f"Unsupported mode: {mode}"}

    if paper_broker != "alpaca":
        broker_kind = "live broker" if mode == "live" else "paper broker"
        return {"error": f"Unsupported {broker_kind}: {paper_broker}"}

    if not alpaca_api_key or not alpaca_api_secret:
        return {"error": "alpaca paper credentials are required (ALPACA_API_KEY/ALPACA_API_SECRET)"}

    if httpx is None:
        return {"error": "httpx not installed. pip install httpx"}

    client_order_id = str(uuid.uuid4())
    request_payload = {
        "symbol": instrument,
        "side": side,
        "type": "market",
        "time_in_force": "day",
        "qty": str(size),
        "client_order_id": client_order_id,
    }
    if stop_loss is not None or take_profit is not None:
        request_payload["order_class"] = "bracket"
        if stop_loss is not None:
            request_payload["stop_loss"] = {"stop_price": str(stop_loss)}
        if take_profit is not None:
            request_payload["take_profit"] = {"limit_price": str(take_profit)}

    try:
        resp = httpx.post(
            (
                "https://api.alpaca.markets/v2/orders"
                if mode == "live"
                else "https://paper-api.alpaca.markets/v2/orders"
            ),
            json=request_payload,
            headers={
                "APCA-API-KEY-ID": alpaca_api_key,
                "APCA-API-SECRET-KEY": alpaca_api_secret,
            },
            timeout=10.0,
        )
        resp.raise_for_status()
        broker_payload = resp.json() if hasattr(resp, "json") else {}
    except Exception as exc:  # noqa: BLE001
        return {"error": f"{mode} trade submission failed: {exc}"}

    order_id = str(broker_payload.get("id") or client_order_id)
    broker_status = str(broker_payload.get("status") or "accepted")
    entry = {
        "ts": now_ts,
        "order_id": order_id,
        "client_order_id": client_order_id,
        "instrument": instrument,
        "side": side,
        "size": size,
        "rationale": rationale,
        "reason": rationale,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "mode": mode,
        "paper_broker": paper_broker,
        "broker_status": broker_status,
        "live_confirm": bool(payload.get("live_confirm")),
        "pnl_delta": float(payload.get("pnl_delta") or 0.0),
    }

    trades_log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(trades_log_path, "a") as f:
        f.write(json.dumps(entry) + "\n")

    return {
        "status": "live_submitted" if mode == "live" else "paper_submitted",
        "order_id": order_id,
        "instrument": instrument,
        "side": side,
        "size": size,
        "rationale": rationale,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "paper_broker": paper_broker,
        "broker_status": broker_status,
    }


def make_trade_tool(
    request_approval: Callable[[str, dict[str, Any]], str] | None = None,
    get_approval: Callable[[str], dict[str, Any] | None] | None = None,
    account_equity: float = 100000.0,
    max_position_pct: float = 2.0,
) -> Tool:
    """Create trade tool with approval gating.

    Args:
        request_approval: Function(kind, payload) -> approval_id
        get_approval: Function(approval_id) -> approval dict

    Returns:
        Tool instance for trade
    """

    def handler(
        instrument: str,
        side: str,
        size: float,
        rationale: str = "",
        stop_loss: float | None = None,
        take_profit: float | None = None,
        live_confirm: bool = False,
        reason: str = "",
    ) -> dict:
        """Handle trade order request.

        Args:
            instrument: Trading pair (AAPL, BTC/USD, EURUSD, etc.)
            side: "buy" or "sell"
            size: Order size (max 10000 units)
            rationale: Trading thesis or rationale
            stop_loss: Optional stop-loss level
            take_profit: Optional take-profit level
            live_confirm: Explicit confirmation required for live trading mode
            reason: Deprecated alias for rationale

        Returns:
            dict with status and correlation_id or error
        """
        proposal = build_trade_proposal(
            instrument=instrument,
            side=side,
            size=size,
            rationale=rationale or reason,
            stop_loss=stop_loss,
            take_profit=take_profit,
        )
        if "error" in proposal:
            return proposal

        if proposal["size"] > 10000:
            return {"error": f"size {size} exceeds position cap of 10000"}

        cap_error = validate_position_size_cap(
            size=proposal["size"],
            account_equity=account_equity,
            max_position_pct=max_position_pct,
        )
        if cap_error:
            return {"error": cap_error}

        payload = dict(proposal)
        payload["reason"] = proposal["rationale"]
        payload["live_confirm"] = bool(live_confirm)

        if not request_approval:
            return {"error": "approval gating not configured"}

        approval_id = request_approval("trade", payload)
        approval = get_approval(approval_id) if get_approval else None

        return {
            "status": "pending_approval",
            "kind": "trade",
            "approval_id": approval_id,
            "correlation_id": approval.get("correlation_id") if approval else None,
            "instrument": proposal["instrument"],
            "side": proposal["side"],
            "size": proposal["size"],
            "rationale": proposal["rationale"],
            "stop_loss": proposal["stop_loss"],
            "take_profit": proposal["take_profit"],
            "live_confirm": bool(live_confirm),
        }

    return Tool(
        name="trade",
        description="Propose a broker trade order (approval-required). Paper trading mode, 10k unit cap.",
        input_schema={
            "type": "object",
            "properties": {
                "instrument": {
                    "type": "string",
                    "description": "Trading pair (AAPL, BTC/USD, EURUSD, etc.)",
                },
                "side": {
                    "type": "string",
                    "enum": ["buy", "sell"],
                    "description": "Buy or sell",
                },
                "size": {
                    "type": "number",
                    "description": "Order size (max 10000 units)",
                },
                "rationale": {
                    "type": "string",
                    "description": "Trading thesis or rationale",
                },
                "stop_loss": {
                    "type": "number",
                    "description": "Optional stop-loss price level",
                },
                "take_profit": {
                    "type": "number",
                    "description": "Optional take-profit price level",
                },
                "live_confirm": {
                    "type": "boolean",
                    "description": "Explicit confirmation required for live trading mode",
                },
                "reason": {
                    "type": "string",
                    "description": "Deprecated alias for rationale",
                },
            },
            "required": ["instrument", "side", "size", "rationale"],
        },
        handler=handler,
        tier="gated",
    )
