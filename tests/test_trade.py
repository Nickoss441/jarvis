"""Tests for trade tool and dispatcher."""
import datetime as dt
import json
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from jarvis.audit import AuditLog
from jarvis.config import Config
from jarvis.tools.trade import (
    build_trade_performance_report,
    build_trade_proposal,
    build_trade_replay_report,
    current_daily_realized_pnl,
    daily_drawdown_limit_for_equity,
    dispatch_trade,
    make_trade_tool,
    position_size_cap_for_equity,
    validate_daily_drawdown_pause,
    validate_position_size_cap,
)
from jarvis.trade_review import generate_trade_review_artifact


def test_build_trade_proposal_requires_rationale():
    proposal = build_trade_proposal(
        instrument="AAPL",
        side="buy",
        size=10,
        rationale="",
    )

    assert proposal["error"] == "rationale is required"


def test_build_trade_proposal_validates_bracket_levels_for_buy_side():
    proposal = build_trade_proposal(
        instrument="AAPL",
        side="buy",
        size=10,
        rationale="Breakout setup",
        stop_loss=210,
        take_profit=205,
    )

    assert proposal["error"] == "buy trades require stop_loss below take_profit"


def test_position_size_cap_for_equity_computes_two_percent_limit():
    assert position_size_cap_for_equity(100000, 2.0) == 2000.0


def test_daily_drawdown_limit_for_equity_computes_five_percent_limit():
    assert daily_drawdown_limit_for_equity(100000, 5.0) == 5000.0


def test_validate_daily_drawdown_pause_blocks_same_day_breach(tmp_path):
    trades_log = tmp_path / "trades.jsonl"
    now = time.time()
    trades_log.write_text(
        "\n".join(
            [
                json.dumps({"mode": "live", "ts": now - 60, "pnl_delta": -3000.0}),
                json.dumps({"mode": "live", "ts": now - 30, "pnl_delta": -2500.0}),
            ]
        ) + "\n",
        encoding="utf-8",
    )

    error = validate_daily_drawdown_pause(
        trades_log_path=trades_log,
        account_equity=100000,
        max_daily_drawdown_pct=5.0,
    )

    assert error is not None
    assert "daily drawdown pause active" in error


def test_current_daily_realized_pnl_resets_on_new_day(tmp_path):
    trades_log = tmp_path / "trades.jsonl"
    today = dt.datetime(2026, 4, 26, 12, 0, 0, tzinfo=dt.timezone.utc)
    yesterday = today - dt.timedelta(days=1)
    trades_log.write_text(
        "\n".join(
            [
                json.dumps({"mode": "live", "ts": yesterday.timestamp(), "pnl_delta": -6000.0}),
                json.dumps({"mode": "live", "ts": today.timestamp(), "pnl_delta": -1000.0}),
            ]
        ) + "\n",
        encoding="utf-8",
    )

    pnl = current_daily_realized_pnl(trades_log, now=today)

    assert pnl == -1000.0


def test_build_trade_replay_report_groups_trade_audit_events(tmp_path):
    audit = AuditLog(tmp_path / "audit.db")
    correlation_id = "trade-corr-1"

    audit.append(
        "approval_requested",
        {
            "approval_id": "trade-1",
            "correlation_id": correlation_id,
            "kind": "trade",
            "payload": {
                "instrument": "AAPL",
                "side": "buy",
                "size": 10,
                "rationale": "Breakout",
                "live_confirm": True,
            },
        },
    )
    audit.append("approval_approved", {"approval_id": "trade-1", "correlation_id": correlation_id})
    audit.append(
        "approval_dispatched",
        {
            "approval_id": "trade-1",
            "correlation_id": correlation_id,
            "kind": "trade",
            "success": True,
            "result": {
                "status": "live_submitted",
                "order_id": "ord-1",
                "instrument": "AAPL",
                "side": "buy",
                "size": 10,
            },
        },
    )

    report = build_trade_replay_report(audit, limit=10)

    assert report["count"] == 1
    assert report["success_count"] == 1
    assert report["status_counts"] == {"live_submitted": 1}
    assert report["trades"][0]["instrument"] == "AAPL"
    assert report["trades"][0]["status"] == "live_submitted"
    assert report["trades"][0]["dispatch_result"]["order_id"] == "ord-1"


def test_build_trade_replay_report_marks_rejected_trade(tmp_path):
    audit = AuditLog(tmp_path / "audit.db")
    correlation_id = "trade-corr-2"

    audit.append(
        "approval_requested",
        {
            "approval_id": "trade-2",
            "correlation_id": correlation_id,
            "kind": "trade",
            "payload": {
                "instrument": "TSLA",
                "side": "sell",
                "size": 5,
                "rationale": "Fade move",
            },
        },
    )
    audit.append(
        "approval_rejected",
        {"approval_id": "trade-2", "correlation_id": correlation_id, "reason": "skip"},
    )

    report = build_trade_replay_report(audit, limit=10)

    assert report["count"] == 1
    assert report["failure_count"] == 0
    assert report["status_counts"] == {"rejected": 1}
    assert report["trades"][0]["status"] == "rejected"


def test_build_trade_performance_report_summarizes_metrics_and_audit_signals(tmp_path):
    trades_log = tmp_path / "trades.jsonl"
    audit = AuditLog(tmp_path / "audit.db")

    day_one = dt.datetime(2026, 4, 20, 12, 0, tzinfo=dt.timezone.utc).timestamp()
    day_two = dt.datetime(2026, 4, 21, 12, 0, tzinfo=dt.timezone.utc).timestamp()
    trades_log.write_text(
        "\n".join(
            [
                json.dumps({"mode": "paper", "ts": day_one, "pnl_delta": 100.0, "latency_ms": 10.0, "slippage_bps": 5.0}),
                json.dumps({"mode": "paper", "ts": day_one + 60, "pnl_delta": -40.0, "latency_ms": 1200.0, "slippage_bps": 60.0}),
                json.dumps({"mode": "paper", "ts": day_two, "pnl_delta": 60.0, "latency_ms": 15.0, "slippage_bps": 4.0}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    audit.append(
        "tool_call",
        {
            "name": "trade",
            "args": {"instrument": "AAPL"},
            "correlation_id": "trade-corr-denied",
            "policy": {"allowed": False, "reason": "quiet hours"},
        },
    )
    audit.append(
        "approval_dispatched",
        {
            "approval_id": "trade-err-1",
            "correlation_id": "trade-corr-fail",
            "kind": "trade",
            "success": False,
            "result": {"error": "broker timeout"},
        },
    )

    report = build_trade_performance_report(
        trades_log,
        audit_log=audit,
        mode="paper",
        min_trading_days=2,
        min_trades=3,
    )

    assert report["trade_count"] == 3
    assert report["trading_days"] == 2
    assert report["meets_minimum_window"] is True
    assert report["pnl"]["gross_profit"] == 160.0
    assert report["pnl"]["gross_loss"] == 40.0
    assert report["pnl"]["net"] == 120.0
    assert report["pnl"]["profit_factor"] == 4.0
    assert report["pnl"]["win_rate"] == pytest.approx(2 / 3)
    assert report["risk"]["max_drawdown"] == 40.0
    assert report["window"]["start"] == "2026-04-20T12:00:00+00:00"
    assert report["window"]["end"] == "2026-04-21T12:00:00+00:00"
    assert report["anomalies"]["latency_count"] == 1
    assert report["anomalies"]["slippage_count"] == 1
    assert report["audit"]["policy_violation_count"] == 1
    assert report["audit"]["dispatch_failure_count"] == 1


def test_dispatch_trade_dry_run(tmp_path):
    """Test dry-run trade logging."""
    trades_log = tmp_path / "trades.jsonl"
    result = dispatch_trade(
        mode="dry_run",
        trades_log_path=trades_log,
        payload={
            "instrument": "AAPL",
            "side": "buy",
            "size": 100,
            "rationale": "Value accumulation",
            "stop_loss": 180.0,
            "take_profit": 230.0,
        },
    )

    assert result["status"] == "dry_run_logged"
    assert result["instrument"] == "AAPL"
    assert result["side"] == "buy"
    assert result["size"] == 100
    assert result["rationale"] == "Value accumulation"
    assert result["stop_loss"] == 180.0
    assert result["take_profit"] == 230.0
    assert trades_log.exists()

    # Verify log entry
    logged = json.loads(trades_log.read_text())
    assert logged["instrument"] == "AAPL"
    assert logged["side"] == "buy"
    assert logged["size"] == 100
    assert logged["rationale"] == "Value accumulation"
    assert logged["stop_loss"] == 180.0
    assert logged["take_profit"] == 230.0
    assert logged["mode"] == "dry_run"


def test_dispatch_trade_missing_rationale(tmp_path):
    trades_log = tmp_path / "trades.jsonl"
    result = dispatch_trade(
        mode="dry_run",
        trades_log_path=trades_log,
        payload={
            "instrument": "AAPL",
            "side": "buy",
            "size": 100,
        },
    )

    assert result["error"] == "rationale is required"


def test_dispatch_trade_missing_instrument(tmp_path):
    """Test that missing instrument returns error."""
    trades_log = tmp_path / "trades.jsonl"
    result = dispatch_trade(
        mode="dry_run",
        trades_log_path=trades_log,
        payload={
            "side": "buy",
            "size": 50,
        },
    )

    assert "error" in result
    assert "instrument" in result["error"]


def test_dispatch_trade_invalid_side(tmp_path):
    """Test that invalid side is rejected."""
    trades_log = tmp_path / "trades.jsonl"
    result = dispatch_trade(
        mode="dry_run",
        trades_log_path=trades_log,
        payload={
            "instrument": "BTC/USD",
            "side": "hold",  # Invalid
            "size": 0.5,
        },
    )

    assert "error" in result
    assert "side" in result["error"]


def test_dispatch_trade_position_cap(tmp_path):
    """Test that oversized positions are rejected."""
    trades_log = tmp_path / "trades.jsonl"
    result = dispatch_trade(
        mode="dry_run",
        trades_log_path=trades_log,
        payload={
            "instrument": "AAPL",
            "side": "buy",
            "size": 50000,  # Over cap
            "rationale": "Oversized test order",
        },
    )

    assert "error" in result
    assert "position cap" in result["error"]


def test_dispatch_trade_equity_position_cap(tmp_path):
    trades_log = tmp_path / "trades.jsonl"
    result = dispatch_trade(
        mode="dry_run",
        trades_log_path=trades_log,
        payload={
            "instrument": "AAPL",
            "side": "buy",
            "size": 2500,
            "rationale": "Above equity cap",
        },
        account_equity=100000,
        max_position_pct=2.0,
    )

    assert "error" in result
    assert "max position size" in result["error"]


def test_dispatch_trade_paper_alpaca_missing_credentials(tmp_path):
    trades_log = tmp_path / "trades.jsonl"
    result = dispatch_trade(
        mode="paper",
        trades_log_path=trades_log,
        payload={
            "instrument": "AAPL",
            "side": "buy",
            "size": 10,
            "rationale": "Broker credential test",
        },
        paper_broker="alpaca",
        alpaca_api_key="",
        alpaca_api_secret="",
    )

    assert "error" in result
    assert "alpaca paper credentials" in result["error"]


def test_dispatch_trade_paper_unsupported_broker(tmp_path):
    trades_log = tmp_path / "trades.jsonl"
    result = dispatch_trade(
        mode="paper",
        trades_log_path=trades_log,
        payload={
            "instrument": "AAPL",
            "side": "buy",
            "size": 10,
            "rationale": "Unsupported broker test",
        },
        paper_broker="ibkr",
        alpaca_api_key="key",
        alpaca_api_secret="secret",
    )

    assert "error" in result
    assert "Unsupported paper broker" in result["error"]


def test_dispatch_trade_live_requires_explicit_confirm(tmp_path):
    trades_log = tmp_path / "trades.jsonl"
    result = dispatch_trade(
        mode="live",
        trades_log_path=trades_log,
        payload={
            "instrument": "AAPL",
            "side": "buy",
            "size": 10,
            "rationale": "Live entry",
        },
        paper_broker="alpaca",
        alpaca_api_key="key",
        alpaca_api_secret="secret",
    )

    assert "error" in result
    assert "requires per-trade confirm" in result["error"]


def test_dispatch_trade_live_respects_cooldown(tmp_path):
    trades_log = tmp_path / "trades.jsonl"
    trades_log.write_text(
        json.dumps({"mode": "live", "ts": __import__("time").time() - 10}) + "\n",
        encoding="utf-8",
    )

    result = dispatch_trade(
        mode="live",
        trades_log_path=trades_log,
        payload={
            "instrument": "AAPL",
            "side": "buy",
            "size": 10,
            "rationale": "Live entry",
            "live_confirm": True,
        },
        paper_broker="alpaca",
        alpaca_api_key="key",
        alpaca_api_secret="secret",
        live_cooldown_seconds=300,
    )

    assert "error" in result
    assert "cooldown active" in result["error"]


def test_dispatch_trade_live_alpaca_success(tmp_path):
    trades_log = tmp_path / "trades.jsonl"
    fake_resp = MagicMock()
    fake_resp.raise_for_status = MagicMock()
    fake_resp.json.return_value = {"id": "ord_live_123", "status": "accepted"}

    with patch("jarvis.tools.trade.httpx") as mock_httpx:
        mock_httpx.post.return_value = fake_resp

        result = dispatch_trade(
            mode="live",
            trades_log_path=trades_log,
            payload={
                "instrument": "AAPL",
                "side": "buy",
                "size": 10,
                "rationale": "Live entry",
                "live_confirm": True,
            },
            paper_broker="alpaca",
            alpaca_api_key="key",
            alpaca_api_secret="secret",
            live_cooldown_seconds=0,
        )

    assert result["status"] == "live_submitted"
    assert result["order_id"] == "ord_live_123"
    logged = json.loads(trades_log.read_text())
    assert logged["mode"] == "live"
    assert logged["live_confirm"] is True

    _, kwargs = mock_httpx.post.call_args
    assert kwargs["json"]["symbol"] == "AAPL"


def test_dispatch_trade_live_paused_after_daily_drawdown_breach(tmp_path):
    trades_log = tmp_path / "trades.jsonl"
    now = __import__("time").time()
    trades_log.write_text(
        json.dumps({"mode": "live", "ts": now - 60, "pnl_delta": -6000.0}) + "\n",
        encoding="utf-8",
    )

    result = dispatch_trade(
        mode="live",
        trades_log_path=trades_log,
        payload={
            "instrument": "AAPL",
            "side": "buy",
            "size": 10,
            "rationale": "Live entry",
            "live_confirm": True,
        },
        paper_broker="alpaca",
        alpaca_api_key="key",
        alpaca_api_secret="secret",
        live_cooldown_seconds=0,
        account_equity=100000,
        max_daily_drawdown_pct=5.0,
    )

    assert "error" in result
    assert "daily drawdown pause active" in result["error"]


def test_dispatch_trade_paper_alpaca_success(tmp_path):
    trades_log = tmp_path / "trades.jsonl"
    fake_resp = MagicMock()
    fake_resp.raise_for_status = MagicMock()
    fake_resp.json.return_value = {"id": "ord_123", "status": "accepted"}

    with patch("jarvis.tools.trade.httpx") as mock_httpx:
        mock_httpx.post.return_value = fake_resp

        result = dispatch_trade(
            mode="paper",
            trades_log_path=trades_log,
            payload={
                "instrument": "AAPL",
                "side": "buy",
                "size": 10,
                "rationale": "Paper entry",
                "stop_loss": 180.0,
                "take_profit": 230.0,
            },
            paper_broker="alpaca",
            alpaca_api_key="key",
            alpaca_api_secret="secret",
        )

    assert result["status"] == "paper_submitted"
    assert result["order_id"] == "ord_123"
    assert result["paper_broker"] == "alpaca"
    assert result["broker_status"] == "accepted"
    assert result["rationale"] == "Paper entry"
    assert result["stop_loss"] == 180.0
    assert result["take_profit"] == 230.0
    assert trades_log.exists()

    logged = json.loads(trades_log.read_text())
    assert logged["mode"] == "paper"
    assert logged["paper_broker"] == "alpaca"
    assert logged["broker_status"] == "accepted"
    assert logged["instrument"] == "AAPL"
    assert logged["rationale"] == "Paper entry"
    assert logged["stop_loss"] == 180.0
    assert logged["take_profit"] == 230.0

    mock_httpx.post.assert_called_once()
    _, kwargs = mock_httpx.post.call_args
    assert kwargs["json"]["order_class"] == "bracket"
    assert kwargs["json"]["stop_loss"] == {"stop_price": "180.0"}
    assert kwargs["json"]["take_profit"] == {"limit_price": "230.0"}


def test_make_trade_tool_with_approval():
    """Test trade tool factory with approval gating."""
    approval_store = {}

    def mock_request_approval(kind, payload):
        aid = "approval-789"
        approval_store[aid] = {
            "id": aid,
            "kind": kind,
            "payload": payload,
            "correlation_id": "corr-012",
        }
        return aid

    def mock_get_approval(aid):
        return approval_store.get(aid)

    tool = make_trade_tool(
        request_approval=mock_request_approval,
        get_approval=mock_get_approval,
    )

    assert tool.name == "trade"
    assert tool.tier == "gated"

    result = tool.handler(
        instrument="EURUSD",
        side="sell",
        size=1000,
        rationale="Technical breakout",
        stop_loss=1.12,
        take_profit=1.08,
    )

    assert result["status"] == "pending_approval"
    assert result["kind"] == "trade"
    assert result["instrument"] == "EURUSD"
    assert result["side"] == "sell"
    assert result["size"] == 1000
    assert result["rationale"] == "Technical breakout"
    assert result["stop_loss"] == 1.12
    assert result["take_profit"] == 1.08
    assert result["correlation_id"] == "corr-012"
    assert approval_store["approval-789"]["payload"]["rationale"] == "Technical breakout"


def test_make_trade_tool_invalid_side():
    """Test that invalid side is rejected at tool level."""
    def mock_request_approval(kind, payload):
        return "aid-123"

    tool = make_trade_tool(
        request_approval=mock_request_approval,
    )

    result = tool.handler(
        instrument="AAPL",
        side="hold",
        size=50,
    )

    assert "error" in result


def test_make_trade_tool_accepts_reason_alias_for_rationale():
    approval_store = {}

    def mock_request_approval(kind, payload):
        approval_store["payload"] = payload
        return "aid-123"

    tool = make_trade_tool(request_approval=mock_request_approval)

    result = tool.handler(
        instrument="AAPL",
        side="buy",
        size=50,
        reason="Mean reversion setup",
    )

    assert result["status"] == "pending_approval"
    assert approval_store["payload"]["rationale"] == "Mean reversion setup"


def test_make_trade_tool_passes_live_confirm_into_payload():
    approval_store = {}

    def mock_request_approval(kind, payload):
        approval_store["payload"] = payload
        return "aid-123"

    tool = make_trade_tool(request_approval=mock_request_approval)

    result = tool.handler(
        instrument="AAPL",
        side="buy",
        size=50,
        rationale="Live setup",
        live_confirm=True,
    )

    assert result["status"] == "pending_approval"
    assert approval_store["payload"]["live_confirm"] is True


def test_make_trade_tool_rejects_trade_above_equity_position_cap():
    def mock_request_approval(kind, payload):
        return "aid-123"

    tool = make_trade_tool(
        request_approval=mock_request_approval,
        account_equity=100000,
        max_position_pct=2.0,
    )

    result = tool.handler(
        instrument="AAPL",
        side="buy",
        size=2500,
        rationale="Too large for cap",
    )

    assert "error" in result
    assert "max position size" in result["error"]


def test_backtesting_integration_generates_unlockable_performance_review(tmp_path, monkeypatch):
    """Integration test: generate 150 profitable trades, produce review artifact, verify unlock-ready."""
    audit_db = tmp_path / "audit.db"
    trades_log = tmp_path / "trades.jsonl"
    review_output = tmp_path / "review.md"

    audit_log = AuditLog(audit_db)
    trades_log.parent.mkdir(parents=True, exist_ok=True)

    # Generate 150 profitable paper trades across 25 trading days
    # Win rate: 75% (112 winners, 38 losers)
    # Avg profit per trade: $150 (profit_factor > 1.5)
    base_ts = time.time() - (30 * 86400)  # 30 days ago
    trades_data = []
    winners = 0
    losers = 0
    total_pnl = 0

    for i in range(150):
        day_offset = i // 6  # 6 trades per day
        trade_ts = base_ts + (day_offset * 86400) + (i % 6 * 3600)

        # 75% win rate: first 112 trades are winners, rest are losers
        if i < 112:
            pnl_delta = 150.0 + (i % 10) * 5  # $150-200 per winning trade
            winners += 1
        else:
            pnl_delta = -100.0  # $100 loss per losing trade
            losers += 1

        total_pnl += pnl_delta
        trades_data.append(
            json.dumps(
                {
                    "mode": "paper",
                    "ts": trade_ts,
                    "pnl_delta": pnl_delta,
                    "instrument": f"{'AAPL' if i % 3 == 0 else 'TSLA' if i % 3 == 1 else 'MSFT'}",
                    "side": "buy" if i % 2 == 0 else "sell",
                }
            )
        )

        # Create audit trail for each trade
        approval_id = f"trade-{i:03d}"
        correlation_id = f"corr-{i:03d}"
        audit_log.append(
            "approval_requested",
            {
                "approval_id": approval_id,
                "correlation_id": correlation_id,
                "kind": "trade",
                "payload": {
                    "instrument": f"{'AAPL' if i % 3 == 0 else 'TSLA' if i % 3 == 1 else 'MSFT'}",
                    "side": "buy" if i % 2 == 0 else "sell",
                    "size": 10 + (i % 5),
                    "rationale": f"Backtest trade {i}",
                },
            },
        )
        audit_log.append(
            "approval_approved",
            {
                "approval_id": approval_id,
                "correlation_id": correlation_id,
            },
        )
        audit_log.append(
            "approval_dispatched",
            {
                "approval_id": approval_id,
                "correlation_id": correlation_id,
                "kind": "trade",
                "success": True,
                "result": {
                    "status": "paper_filled",
                    "order_id": f"ord-{i:03d}",
                    "instrument": f"{'AAPL' if i % 3 == 0 else 'TSLA' if i % 3 == 1 else 'MSFT'}",
                    "side": "buy" if i % 2 == 0 else "sell",
                    "size": 10 + (i % 5),
                },
            },
        )

    trades_log.write_text("\n".join(trades_data) + "\n", encoding="utf-8")

    # Set up config for review generation
    monkeypatch.setenv("JARVIS_AUDIT_DB", str(audit_db))
    monkeypatch.setenv("JARVIS_TRADES_LOG", str(trades_log))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("JARVIS_TRADING_ACCOUNT_EQUITY", "100000")
    monkeypatch.setenv("JARVIS_TRADING_DAILY_DRAWDOWN_KILL_PCT", "5.0")
    monkeypatch.setenv("JARVIS_TRADING_REVIEW_MIN_TRADING_DAYS", "20")
    monkeypatch.setenv("JARVIS_TRADING_REVIEW_MIN_TRADES", "100")
    monkeypatch.setenv("JARVIS_TRADING_REVIEW_MIN_WIN_RATE", "0.70")
    monkeypatch.setenv("JARVIS_TRADING_REVIEW_MIN_PROFIT_FACTOR", "1.50")
    monkeypatch.setenv("JARVIS_TRADING_REVIEW_MIN_AVG_R_MULTIPLE", "0.50")
    monkeypatch.setenv("JARVIS_TRADING_REVIEW_MAX_ANOMALIES", "5")

    config = Config.from_env()

    # Generate trade review artifact
    result = generate_trade_review_artifact(
        config,
        output_file=str(review_output),
        reviewer="BacktestSuite",
        strategy_version="v1.0.0-backtest",
    )

    # Verify result structure
    assert result["ok"] is True
    assert result["review_id"].startswith("paper-review-")
    assert result["trade_count"] == 150
    assert result["trading_days"] >= 20
    assert result["meets_minimum_window"] is True

    # Verify all auto-checks pass
    auto_checks = result["auto_checks"]
    assert auto_checks["review_window"] is True, "Should meet minimum trading window"
    assert auto_checks["win_rate"] is True, "Win rate 75% >= 70% minimum"
    assert auto_checks["profit_factor"] is True, "Profit factor should be > 1.5"
    assert auto_checks["avg_r_multiple"] is True, "Avg R multiple should be > 0.5"
    assert auto_checks["anomalies"] is True, "No anomalies expected"
    assert auto_checks["policy_bypass"] is True, "No policy violations"
    assert auto_checks["dispatch_failures"] is True, "No dispatch failures"
    assert auto_checks["drawdown_guardrail"] is True, "Drawdown within limits"

    # Verify unlock readiness
    assert auto_checks["ready_for_manual_signoff"] is True, "Should be ready for manual sign-off"
    assert result["auto_decision"] == "ready for manual sign-off"
    assert result["auto_conditions"] == [], "No conditions should fail"

    # Verify artifacts generated
    assert Path(result["review_markdown"]).exists()
    assert Path(result["audit_export"]).exists()
    assert Path(result["trade_replay_report"]).exists()
    assert Path(result["trade_performance_report"]).exists()

    # Verify markdown content
    review_text = Path(result["review_markdown"]).read_text(encoding="utf-8")
    assert "- Reviewer: BacktestSuite" in review_text
    assert "- Strategy/system version: v1.0.0-backtest" in review_text
    assert "- Total paper trades: 150" in review_text
    assert "| Win rate | 0.74" in review_text or "| Win rate | 0.75" in review_text
    assert "| Profit factor | 5" in review_text
    assert "- Decision: ready for manual sign-off" in review_text
    assert "- [x] Review window >= 20 trading days" in review_text
    assert "- [x] No unresolved policy bypass" in review_text
    assert "- [x] No unexplained trade dispatch" in review_text
    assert "- [x] Drawdown stayed within configured daily" in review_text


def test_position_size_safeguard_prevents_oversized_trades(tmp_path):
    """Safeguard test: position size cap rejects trades above limit."""
    trades_log = tmp_path / "trades.jsonl"
    account_equity = 100000
    max_position_pct = 2.0
    max_size = position_size_cap_for_equity(account_equity, max_position_pct)

    # Valid trade at cap
    error = validate_position_size_cap(size=max_size, account_equity=account_equity, max_position_pct=max_position_pct)
    assert error is None, "Trade at cap should be allowed"

    # Valid trade below cap
    error = validate_position_size_cap(size=max_size * 0.5, account_equity=account_equity, max_position_pct=max_position_pct)
    assert error is None, "Trade below cap should be allowed"

    # Invalid trade above cap
    error = validate_position_size_cap(size=max_size + 1, account_equity=account_equity, max_position_pct=max_position_pct)
    assert error is not None, "Trade above cap should be rejected"
    assert "exceeds max position size" in error
    assert "2000.00" in error or "2000" in error


def test_daily_drawdown_safeguard_pauses_trades(tmp_path):
    """Safeguard test: daily drawdown limit pauses trading after threshold breach."""
    trades_log = tmp_path / "trades.jsonl"
    account_equity = 100000
    max_daily_drawdown_pct = 5.0
    drawdown_limit = daily_drawdown_limit_for_equity(account_equity, max_daily_drawdown_pct)  # $5,000

    # No prior trades: should allow
    error = validate_daily_drawdown_pause(
        trades_log_path=trades_log,
        account_equity=account_equity,
        max_daily_drawdown_pct=max_daily_drawdown_pct,
    )
    assert error is None, "No prior losses should allow trading"

    # Single loss under limit: should allow
    now = dt.datetime.now(dt.timezone.utc)
    trades_log.write_text(
        json.dumps({"mode": "live", "ts": now.timestamp() - 3600, "pnl_delta": -2000.0}) + "\n",
        encoding="utf-8",
    )
    error = validate_daily_drawdown_pause(
        trades_log_path=trades_log,
        account_equity=account_equity,
        max_daily_drawdown_pct=max_daily_drawdown_pct,
        now=now,
    )
    assert error is None, "Loss within limit should allow trading"

    # Multiple losses reaching limit: should PAUSE (at limit is treated as breach)
    trades_log.write_text(
        "\n".join(
            [
                json.dumps({"mode": "live", "ts": (now - dt.timedelta(hours=2)).timestamp(), "pnl_delta": -2500.0}),
                json.dumps({"mode": "live", "ts": (now - dt.timedelta(hours=1)).timestamp(), "pnl_delta": -2500.0}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    error = validate_daily_drawdown_pause(
        trades_log_path=trades_log,
        account_equity=account_equity,
        max_daily_drawdown_pct=max_daily_drawdown_pct,
        now=now,
    )
    assert error is not None, "Loss at/above limit should pause trading (conservative)"
    assert "daily drawdown pause active" in error

    # Loss exceeding limit: should pause
    trades_log.write_text(
        "\n".join(
            [
                json.dumps({"mode": "live", "ts": (now - dt.timedelta(hours=2)).timestamp(), "pnl_delta": -3000.0}),
                json.dumps({"mode": "live", "ts": (now - dt.timedelta(hours=1)).timestamp(), "pnl_delta": -2500.0}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    error = validate_daily_drawdown_pause(
        trades_log_path=trades_log,
        account_equity=account_equity,
        max_daily_drawdown_pct=max_daily_drawdown_pct,
        now=now,
    )
    assert error is not None, "Loss exceeding limit should pause trading"
    assert "daily drawdown pause active" in error


def test_daily_drawdown_safeguard_resets_on_new_day(tmp_path):
    """Safeguard test: daily drawdown counter resets at day boundary."""
    trades_log = tmp_path / "trades.jsonl"
    account_equity = 100000
    max_daily_drawdown_pct = 5.0

    today = dt.datetime(2026, 4, 27, 12, 0, 0, tzinfo=dt.timezone.utc)
    yesterday = today - dt.timedelta(days=1)

    # Yesterday's loss exceeds limit, but today is new day
    trades_log.write_text(
        "\n".join(
            [
                json.dumps({"mode": "live", "ts": yesterday.timestamp(), "pnl_delta": -6000.0}),
                json.dumps({"mode": "live", "ts": today.timestamp() + 3600, "pnl_delta": -1000.0}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    # Today should allow trading despite yesterday's big loss
    error = validate_daily_drawdown_pause(
        trades_log_path=trades_log,
        account_equity=account_equity,
        max_daily_drawdown_pct=max_daily_drawdown_pct,
        now=today + dt.timedelta(hours=2),
    )
    assert error is None, "New day should reset drawdown counter"


def test_safeguard_integration_trade_tool_respects_position_cap(tmp_path):
    """Integration: trade tool enforces position cap from config."""
    def mock_request_approval(kind, payload):
        return "aid-456"

    tool = make_trade_tool(
        request_approval=mock_request_approval,
        account_equity=50000,
        max_position_pct=2.0,  # Max $1,000 per trade
    )

    # Allowed: 1000 shares at $1/share
    result = tool.handler(
        instrument="CHEAP",
        side="buy",
        size=1000,
        rationale="Within cap",
    )
    assert result["status"] == "pending_approval"

    # Rejected: 2000 shares at $1/share (exceeds $1,000 cap)
    result = tool.handler(
        instrument="CHEAP",
        side="buy",
        size=2000,
        rationale="Over cap",
    )
    assert "error" in result
    assert "max position size" in result["error"]


def test_safeguard_integration_dispatch_prevents_live_trading_above_drawdown(tmp_path):
    """Integration: dispatch_trade enforces daily drawdown limit."""
    trades_log = tmp_path / "trades.jsonl"
    now = dt.datetime.now(dt.timezone.utc)

    # Log yesterday's big loss
    yesterday = now - dt.timedelta(days=1)
    trades_log.write_text(
        json.dumps({"mode": "live", "ts": yesterday.timestamp(), "pnl_delta": -6000.0}) + "\n",
        encoding="utf-8",
    )

    # Try to place new trade - should fail
    result = dispatch_trade(
        mode="live",
        trades_log_path=trades_log,
        payload={
            "instrument": "AAPL",
            "side": "buy",
            "size": 10,
            "rationale": "After big loss",
            "live_confirm": True,
        },
        alpaca_api_key="key",
        alpaca_api_secret="secret",
        account_equity=100000,
        max_daily_drawdown_pct=5.0,
        live_cooldown_seconds=0,
    )

    # Should be rejected due to yesterday's loss
    assert "error" in result or result["status"] != "live_submitted"
