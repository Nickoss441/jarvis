import sqlite3
import time
import errno
import json
import uuid
from pathlib import Path

from jarvis.approval import ApprovalStore
from jarvis.__main__ import main
from jarvis.audit import AuditLog
from jarvis.event_bus import EventBus, Event


def test_main_no_args_calls_repl(monkeypatch):
    called = {"repl": False}

    def _fake_repl():
        called["repl"] = True

    monkeypatch.setattr("jarvis.__main__.repl", _fake_repl)

    rc = main([])

    assert rc == 0
    assert called["repl"] is True


def test_main_stop_creates_sentinel_file(tmp_path, monkeypatch, capsys):
    sentinel = tmp_path / "stopped"
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)

    rc = main(["stop"])
    out = capsys.readouterr().out

    assert rc == 0
    assert (tmp_path / ".jarvis" / "stopped").exists()
    assert "Jarvis stopped" in out


def test_main_resume_removes_sentinel_file(tmp_path, monkeypatch, capsys):
    # Create the sentinel file
    sentinel_dir = tmp_path / ".jarvis"
    sentinel_dir.mkdir(parents=True, exist_ok=True)
    sentinel = sentinel_dir / "stopped"
    sentinel.write_text("123", encoding="utf-8")
    
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)

    rc = main(["resume"])
    out = capsys.readouterr().out

    assert rc == 0
    assert not sentinel.exists()
    assert "Jarvis resumed" in out


def test_main_resume_succeeds_when_no_sentinel_file(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)

    rc = main(["resume"])
    out = capsys.readouterr().out

    assert rc == 0
    assert "not stopped" in out


def test_main_audit_verify_success(tmp_path, monkeypatch, capsys):
    db = tmp_path / "audit.db"
    log = AuditLog(db)
    log.append("test", {"ok": True})

    monkeypatch.setenv("JARVIS_AUDIT_DB", str(db))

    rc = main(["audit-verify"])
    out = capsys.readouterr().out

    assert rc == 0
    assert "Audit OK" in out


def test_main_audit_verify_failure(tmp_path, monkeypatch, capsys):
    db = tmp_path / "audit.db"
    log = AuditLog(db)
    log.append("test", {"ok": True})

    with sqlite3.connect(db) as con:
        con.execute("UPDATE events SET payload = ? WHERE id = 1", ('{"ok": false}',))

    monkeypatch.setenv("JARVIS_AUDIT_DB", str(db))

    rc = main(["audit-verify"])
    out = capsys.readouterr().out

    assert rc == 2
    assert "Audit FAILED" in out


def test_main_audit_export_streams_jsonl(tmp_path, monkeypatch, capsys):
    db = tmp_path / "audit.db"
    log = AuditLog(db)
    log.append("k1", {"n": 1})
    log.append("k2", {"n": 2})

    monkeypatch.setenv("JARVIS_AUDIT_DB", str(db))

    rc = main(["audit-export"])
    out = capsys.readouterr().out
    lines = [line for line in out.splitlines() if line.strip()]

    assert rc == 0
    assert len(lines) == 2
    parsed = [json.loads(line) for line in lines]
    assert [row["kind"] for row in parsed] == ["k1", "k2"]


def test_main_audit_stats_prints_pretty_json(tmp_path, monkeypatch, capsys):
    db = tmp_path / "audit.db"
    log = AuditLog(db)
    log.append("alpha", {"n": 1})
    log.append("beta", {"n": 2})

    monkeypatch.setenv("JARVIS_AUDIT_DB", str(db))

    rc = main(["audit-stats"])
    out = capsys.readouterr().out
    payload = json.loads(out)

    assert rc == 0
    assert payload["chain_length"] == 2
    assert payload["kinds"] == {"alpha": 1, "beta": 1}
    assert payload["oldest_ts"] <= payload["newest_ts"]


def test_main_trade_replay_report_prints_trade_summary(tmp_path, monkeypatch, capsys):
    db = tmp_path / "audit.db"
    log = AuditLog(db)
    corr = "trade-report-corr"

    log.append(
        "approval_requested",
        {
            "approval_id": "trade-1",
            "correlation_id": corr,
            "kind": "trade",
            "payload": {
                "instrument": "AAPL",
                "side": "buy",
                "size": 3,
                "rationale": "Trend continuation",
            },
        },
    )
    log.append(
        "approval_dispatched",
        {
            "approval_id": "trade-1",
            "correlation_id": corr,
            "kind": "trade",
            "success": True,
            "result": {"status": "paper_submitted", "order_id": "ord-1"},
        },
    )

    monkeypatch.setenv("JARVIS_AUDIT_DB", str(db))

    rc = main(["trade-replay-report", "--limit", "5"])
    out = capsys.readouterr().out
    payload = json.loads(out)

    assert rc == 0
    assert payload["count"] == 1
    assert payload["status_counts"] == {"paper_submitted": 1}
    assert payload["trades"][0]["dispatch_result"]["order_id"] == "ord-1"


def test_main_trade_replay_report_invalid_limit_errors(capsys):
    rc = main(["trade-replay-report", "--limit", "oops"])
    out = capsys.readouterr().out.strip()
    payload = json.loads(out)

    assert rc == 1
    assert payload["ok"] is False
    assert payload["error"] == "invalid_limit_value"


def test_main_trade_performance_report_prints_summary(tmp_path, monkeypatch, capsys):
    db = tmp_path / "audit.db"
    trades_log = tmp_path / "trades.jsonl"
    log = AuditLog(db)

    trades_log.write_text(
        "\n".join(
            [
                json.dumps({"mode": "paper", "ts": 1713744000.0, "pnl_delta": 75.0}),
                json.dumps({"mode": "paper", "ts": 1713830400.0, "pnl_delta": -25.0}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    log.append(
        "tool_call",
        {
            "name": "trade",
            "args": {"instrument": "AAPL"},
            "correlation_id": "trade-report-corr",
            "policy": {"allowed": False, "reason": "quiet hours"},
        },
    )

    monkeypatch.setenv("JARVIS_AUDIT_DB", str(db))
    monkeypatch.setenv("JARVIS_TRADES_LOG", str(trades_log))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    rc = main(["trade-performance-report", "--mode", "paper"])
    out = capsys.readouterr().out
    payload = json.loads(out)

    assert rc == 0
    assert payload["mode"] == "paper"


def test_main_trade_streaks_prints_streak_summary(tmp_path, monkeypatch, capsys):
    trades_log = tmp_path / "trades.jsonl"
    trades_log.write_text(
        "\n".join(
            [
                json.dumps({"mode": "paper", "ts": 1713744000.0, "pnl_delta": 75.0}),
                json.dumps({"mode": "paper", "ts": 1713830400.0, "pnl_delta": -25.0}),
                json.dumps({"mode": "paper", "ts": 1713916800.0, "pnl_delta": -15.0}),
                json.dumps({"mode": "paper", "ts": 1714003200.0, "pnl_delta": 40.0}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    monkeypatch.setenv("JARVIS_TRADES_LOG", str(trades_log))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    rc = main(["trade-streaks", "--mode", "paper", "--limit", "4"])
    out = capsys.readouterr().out
    payload = json.loads(out)

    assert rc == 0
    assert payload["mode"] == "paper"
    assert payload["max_loss_streak"] == 2
    assert payload["current_streak"] == {"type": "win", "count": 1}


def test_main_trade_portfolio_metrics_prints_metrics(tmp_path, monkeypatch, capsys):
    trades_log = tmp_path / "trades.jsonl"
    trades_log.write_text(
        "\n".join(
            [
                json.dumps({"mode": "paper", "ts": 1713744000.0, "pnl_delta": 100.0}),
                json.dumps({"mode": "paper", "ts": 1713830400.0, "pnl_delta": -20.0}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    monkeypatch.setenv("JARVIS_TRADES_LOG", str(trades_log))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    rc = main(["trade-portfolio-metrics", "paper"])
    out = capsys.readouterr().out
    payload = json.loads(out)

    assert rc == 0
    assert payload["total_trades"] == 2
    assert payload["total_pnl"] == 80.0
    assert payload["profit_factor"] == 5.0


def test_main_trade_market_hours_reports_supported_market(capsys):
    rc = main(["trade-market-hours", "BTCUSD", "--market", "CRYPTO"])
    out = capsys.readouterr().out
    payload = json.loads(out)

    assert rc == 0
    assert payload["is_open"] is True
    assert payload["market"] == "CRYPTO"


def test_main_trade_risk_estimate_prints_calculated_risk(capsys):
    rc = main(
        [
            "trade-risk-estimate",
            "--position-size",
            "10",
            "--entry-price",
            "100",
            "--stop-loss-price",
            "95",
            "--take-profit-price",
            "115",
        ]
    )
    out = capsys.readouterr().out
    payload = json.loads(out)

    assert rc == 0
    assert payload["max_loss_total"] == 50.0
    assert payload["reward_to_risk_ratio"] == 3.0


def test_main_trade_journal_writes_audit_entry(tmp_path, monkeypatch, capsys):
    db = tmp_path / "audit.db"
    monkeypatch.setenv("JARVIS_AUDIT_DB", str(db))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    rc = main(
        [
            "trade-journal",
            "trade-42",
            "--setup",
            "Opening range breakout",
            "--lessons",
            "Wait for confirmation",
        ]
    )
    out = capsys.readouterr().out
    payload = json.loads(out)
    events = AuditLog(db).recent(limit=5)

    assert rc == 0
    assert payload["ok"] is True
    assert payload["trade_id"] == "trade-42"
    assert events[0]["kind"] == "trade_journal_entry"
    assert events[0]["payload"]["setup"] == "Opening range breakout"


def test_main_trade_performance_report_invalid_mode_errors(capsys):
    rc = main(["trade-performance-report", "--mode", "swing"])
    out = capsys.readouterr().out.strip()
    payload = json.loads(out)

    assert rc == 1
    assert payload["ok"] is False
    assert payload["error"] == "invalid_mode_value"


def test_main_trade_review_artifact_generates_markdown_and_json_artifacts(tmp_path, monkeypatch, capsys):
    db = tmp_path / "audit.db"
    trades_log = tmp_path / "trades.jsonl"
    review_output = tmp_path / "review.md"
    log = AuditLog(db)

    trades_log.write_text(
        "\n".join(
            [
                json.dumps({"mode": "paper", "ts": 1713744000.0, "pnl_delta": 75.0}),
                json.dumps({"mode": "paper", "ts": 1713830400.0, "pnl_delta": -25.0}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    log.append(
        "approval_requested",
        {
            "approval_id": "trade-1",
            "correlation_id": "trade-corr-1",
            "kind": "trade",
            "payload": {"instrument": "AAPL", "side": "buy", "size": 3, "rationale": "Trend"},
        },
    )

    monkeypatch.setenv("JARVIS_AUDIT_DB", str(db))
    monkeypatch.setenv("JARVIS_TRADES_LOG", str(trades_log))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    rc = main([
        "trade-review-artifact",
        "--reviewer",
        "Ops",
        "--strategy-version",
        "v1.2.3",
        "--output",
        str(review_output),
    ])
    out = capsys.readouterr().out
    payload = json.loads(out)

    assert rc == 0
    assert payload["ok"] is True
    assert Path(payload["review_markdown"]).exists()
    assert Path(payload["audit_export"]).exists()
    assert Path(payload["trade_replay_report"]).exists()
    assert Path(payload["trade_performance_report"]).exists()
    assert payload["auto_checks"]["win_rate"] is True
    assert payload["auto_checks"]["profit_factor"] is True
    assert payload["auto_checks"]["avg_r_multiple"] is True
    assert payload["auto_checks"]["anomalies"] is True
    assert payload["auto_checks"]["policy_bypass"] is True
    assert payload["auto_checks"]["dispatch_failures"] is True
    assert payload["auto_checks"]["drawdown_guardrail"] is True
    assert payload["auto_decision"] == "defer"
    assert payload["auto_conditions"] == ["review_window_below_minimum"]

    review_text = review_output.read_text(encoding="utf-8")
    assert "- Reviewer: Ops" in review_text
    assert "- Strategy/system version: v1.2.3" in review_text
    assert "| Policy violations | 0 | 0 | PASS |" in review_text
    assert "| Profit factor | 3.00 | > 1.00 | PASS |" in review_text
    assert "| Slippage/latency anomalies | 0 | <= 0 | PASS |" in review_text
    assert "- [x] No unresolved policy bypass attempts." in review_text
    assert "- [x] No unexplained trade dispatch failures." in review_text
    assert "- Decision: defer" in review_text
    assert "- review_window_below_minimum" in review_text


def test_main_location_update_and_location_last_roundtrip(tmp_path, monkeypatch, capsys):
    event_db = tmp_path / "event-bus.db"
    monkeypatch.setenv("JARVIS_EVENT_BUS_DB", str(event_db))

    rc_update = main([
        "location-update",
        "52.3676",
        "4.9041",
        "--source",
        "ios-shortcut",
        "--accuracy-m",
        "7.5",
    ])
    update_payload = json.loads(capsys.readouterr().out)

    assert rc_update == 0
    assert update_payload["ok"] is True
    assert update_payload["kind"] == "location_update"
    assert update_payload["source"] == "ios-shortcut"

    rc_last = main(["location-last"])
    last_payload = json.loads(capsys.readouterr().out)

    assert rc_last == 0
    assert last_payload["ok"] is True
    assert last_payload["kind"] == "location_update"
    assert last_payload["payload"]["latitude"] == 52.3676
    assert last_payload["payload"]["longitude"] == 4.9041


def test_main_location_update_invalid_lat_lon_errors(capsys):
    rc = main(["location-update", "north", "east"])
    payload = json.loads(capsys.readouterr().out)

    assert rc == 1
    assert payload["ok"] is False
    assert payload["error"] == "invalid_latitude_longitude"


def test_main_voice_self_test_success(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("JARVIS_NOTES_DIR", str(tmp_path / "notes"))
    monkeypatch.setenv("JARVIS_AUDIT_DB", str(tmp_path / "audit.db"))
    monkeypatch.setenv("JARVIS_USER_NAME", "Nick")

    rc = main(["voice-self-test", "--iterations", "3", "--max-roundtrip-ms", "50"])
    out = capsys.readouterr().out
    payload = json.loads(out)

    assert rc == 0
    assert payload["ok"] is True
    assert payload["iterations"] == 3
    assert payload["success_count"] == 3


def test_main_voice_self_test_fails_strict_latency_threshold(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("JARVIS_NOTES_DIR", str(tmp_path / "notes"))
    monkeypatch.setenv("JARVIS_AUDIT_DB", str(tmp_path / "audit.db"))
    monkeypatch.setenv("JARVIS_USER_NAME", "Nick")

    rc = main(["voice-self-test", "--iterations", "3", "--max-roundtrip-ms", "0.000001"])
    out = capsys.readouterr().out
    payload = json.loads(out)

    assert rc == 2
    assert payload["ok"] is False
    assert payload["latency_ms"]["p95"] > payload["max_roundtrip_ms"]


def test_main_voice_self_test_invalid_iterations_errors(capsys):
    rc = main(["voice-self-test", "--iterations", "oops"])
    out = capsys.readouterr().out.strip()
    payload = json.loads(out)

    assert rc == 1
    assert payload["ok"] is False
    assert payload["error"] == "invalid_iterations_value"


def test_main_audit_correlation_returns_matching_events(tmp_path, monkeypatch, capsys):
    db = tmp_path / "audit.db"
    log = AuditLog(db)
    corr = str(uuid.uuid4())
    other = str(uuid.uuid4())

    log.append("user_input", {"text": "a", "correlation_id": corr})
    log.append("llm_response", {"text": "b", "correlation_id": corr})
    log.append("tool_call", {"name": "x", "correlation_id": other})

    monkeypatch.setenv("JARVIS_AUDIT_DB", str(db))

    rc = main(["audit-correlation", corr])
    out = capsys.readouterr().out
    payload = json.loads(out)

    assert rc == 0
    assert payload["ok"] is True
    assert payload["correlation_id"] == corr
    assert payload["count"] == 2
    assert all(e["payload"].get("correlation_id") == corr for e in payload["events"])


def test_main_audit_correlation_returns_empty_when_not_found(tmp_path, monkeypatch, capsys):
    db = tmp_path / "audit.db"
    log = AuditLog(db)
    log.append("user_input", {"text": "a", "correlation_id": "known"})

    monkeypatch.setenv("JARVIS_AUDIT_DB", str(db))

    rc = main(["audit-correlation", "missing"])
    out = capsys.readouterr().out
    payload = json.loads(out)

    assert rc == 0
    assert payload["ok"] is True
    assert payload["correlation_id"] == "missing"
    assert payload["count"] == 0
    assert payload["events"] == []


def test_main_audit_correlation_can_filter_by_kind(tmp_path, monkeypatch, capsys):
    db = tmp_path / "audit.db"
    log = AuditLog(db)
    corr = "corr-kind"

    log.append("user_input", {"text": "a", "correlation_id": corr})
    log.append("tool_call", {"name": "x", "correlation_id": corr})

    monkeypatch.setenv("JARVIS_AUDIT_DB", str(db))

    rc = main(["audit-correlation", corr, "--kind", "tool_call"])
    out = capsys.readouterr().out
    payload = json.loads(out)

    assert rc == 0
    assert payload["ok"] is True
    assert payload["correlation_id"] == corr
    assert payload["kind"] == "tool_call"
    assert payload["count"] == 1
    assert payload["events"][0]["kind"] == "tool_call"


def test_main_audit_correlation_supports_kind_equals_syntax(tmp_path, monkeypatch, capsys):
    db = tmp_path / "audit.db"
    log = AuditLog(db)
    corr = "corr-eq"
    log.append("llm_response", {"text": "x", "correlation_id": corr})

    monkeypatch.setenv("JARVIS_AUDIT_DB", str(db))

    rc = main(["audit-correlation", corr, "--kind=llm_response"])
    out = capsys.readouterr().out
    payload = json.loads(out)

    assert rc == 0
    assert payload["ok"] is True
    assert payload["count"] == 1
    assert payload["events"][0]["kind"] == "llm_response"


def test_main_audit_correlation_missing_kind_value_errors(capsys):
    rc = main(["audit-correlation", "corr", "--kind"])
    out = capsys.readouterr().out.strip()
    payload = json.loads(out)

    assert rc == 1
    assert payload["ok"] is False
    assert payload["error"] == "missing_kind_value"


def test_main_audit_correlation_empty_kind_equals_value_errors(capsys):
    rc = main(["audit-correlation", "corr", "--kind="])
    out = capsys.readouterr().out.strip()
    payload = json.loads(out)

    assert rc == 1
    assert payload["ok"] is False
    assert payload["error"] == "missing_kind_value"


def test_main_audit_correlation_supports_limit_flag(tmp_path, monkeypatch, capsys):
    db = tmp_path / "audit.db"
    log = AuditLog(db)
    corr = "corr-limit-flag"
    log.append("user_input", {"text": "a", "correlation_id": corr})
    log.append("llm_response", {"text": "b", "correlation_id": corr})

    monkeypatch.setenv("JARVIS_AUDIT_DB", str(db))

    rc = main(["audit-correlation", corr, "--limit", "1"])
    out = capsys.readouterr().out
    payload = json.loads(out)

    assert rc == 0
    assert payload["ok"] is True
    assert payload["count"] == 1


def test_main_audit_correlation_supports_limit_equals_syntax(tmp_path, monkeypatch, capsys):
    db = tmp_path / "audit.db"
    log = AuditLog(db)
    corr = "corr-limit-eq"
    log.append("user_input", {"text": "a", "correlation_id": corr})
    log.append("llm_response", {"text": "b", "correlation_id": corr})

    monkeypatch.setenv("JARVIS_AUDIT_DB", str(db))

    rc = main(["audit-correlation", corr, "--limit=1"])
    out = capsys.readouterr().out
    payload = json.loads(out)

    assert rc == 0
    assert payload["ok"] is True
    assert payload["count"] == 1


def test_main_audit_correlation_missing_limit_value_errors(capsys):
    rc = main(["audit-correlation", "corr", "--limit"])
    out = capsys.readouterr().out.strip()
    payload = json.loads(out)

    assert rc == 1
    assert payload["ok"] is False
    assert payload["error"] == "missing_limit_value"


def test_main_audit_correlation_conflicting_positional_and_flag_limit_errors(capsys):
    rc = main(["audit-correlation", "corr", "5", "--limit", "10"])
    out = capsys.readouterr().out.strip()
    payload = json.loads(out)

    assert rc == 1
    assert payload["ok"] is False
    assert payload["error"] == "conflicting_limit_filters"


def test_main_audit_correlation_conflicting_repeated_limit_flags_error(capsys):
    rc = main(["audit-correlation", "corr", "--limit", "5", "--limit", "10"])
    out = capsys.readouterr().out.strip()
    payload = json.loads(out)

    assert rc == 1
    assert payload["ok"] is False
    assert payload["error"] == "conflicting_limit_filters"


def test_main_audit_correlation_repeated_same_limit_flags_allowed(tmp_path, monkeypatch, capsys):
    db = tmp_path / "audit.db"
    log = AuditLog(db)
    corr = "corr-limit-same"
    log.append("user_input", {"text": "a", "correlation_id": corr})
    log.append("llm_response", {"text": "b", "correlation_id": corr})

    monkeypatch.setenv("JARVIS_AUDIT_DB", str(db))

    rc = main(["audit-correlation", corr, "--limit", "1", "--limit=1"])
    out = capsys.readouterr().out
    payload = json.loads(out)

    assert rc == 0
    assert payload["ok"] is True
    assert payload["count"] == 1


def test_main_audit_correlation_limit_zero_is_normalized_to_minimum_one(
    tmp_path,
    monkeypatch,
    capsys,
):
    db = tmp_path / "audit.db"
    log = AuditLog(db)
    corr = "corr-limit-zero"
    log.append("user_input", {"text": "a", "correlation_id": corr})
    log.append("llm_response", {"text": "b", "correlation_id": corr})

    monkeypatch.setenv("JARVIS_AUDIT_DB", str(db))

    rc = main(["audit-correlation", corr, "--limit", "0"])
    out = capsys.readouterr().out
    payload = json.loads(out)

    assert rc == 0
    assert payload["ok"] is True
    assert payload["count"] == 1


def test_main_audit_correlation_negative_limit_is_normalized_to_minimum_one(
    tmp_path,
    monkeypatch,
    capsys,
):
    db = tmp_path / "audit.db"
    log = AuditLog(db)
    corr = "corr-limit-negative"
    log.append("user_input", {"text": "a", "correlation_id": corr})
    log.append("llm_response", {"text": "b", "correlation_id": corr})

    monkeypatch.setenv("JARVIS_AUDIT_DB", str(db))

    rc = main(["audit-correlation", corr, "--limit", "-5"])
    out = capsys.readouterr().out
    payload = json.loads(out)

    assert rc == 0
    assert payload["ok"] is True
    assert payload["count"] == 1


def test_main_audit_correlation_very_large_limit_is_capped_to_maximum(
    tmp_path,
    monkeypatch,
    capsys,
):
    db = tmp_path / "audit.db"
    log = AuditLog(db)
    corr = "corr-limit-max"
    for i in range(1105):
        log.append("tool_call", {"name": f"t{i}", "correlation_id": corr})

    monkeypatch.setenv("JARVIS_AUDIT_DB", str(db))

    rc = main(["audit-correlation", corr, "--limit", "99999"])
    out = capsys.readouterr().out
    payload = json.loads(out)

    assert rc == 0
    assert payload["ok"] is True
    assert payload["count"] == 1000


def test_main_audit_correlation_conflicting_repeated_kind_flags_error(capsys):
    rc = main(["audit-correlation", "corr", "--kind", "tool_call", "--kind", "llm_response"])
    out = capsys.readouterr().out.strip()
    payload = json.loads(out)

    assert rc == 1
    assert payload["ok"] is False
    assert payload["error"] == "conflicting_kind_filters"


def test_main_audit_correlation_repeated_same_kind_flags_allowed(tmp_path, monkeypatch, capsys):
    db = tmp_path / "audit.db"
    log = AuditLog(db)
    corr = "corr-kind-same"
    log.append("tool_call", {"name": "x", "correlation_id": corr})
    log.append("llm_response", {"text": "b", "correlation_id": corr})

    monkeypatch.setenv("JARVIS_AUDIT_DB", str(db))

    rc = main(["audit-correlation", corr, "--kind", "tool_call", "--kind=tool_call"])
    out = capsys.readouterr().out
    payload = json.loads(out)

    assert rc == 0
    assert payload["ok"] is True
    assert payload["count"] == 1
    assert payload["events"][0]["kind"] == "tool_call"


def test_main_approvals_list_shows_pending(tmp_path, monkeypatch, capsys):
    approvals_db = tmp_path / "approvals.db"
    store = ApprovalStore(approvals_db)
    approval_id = store.request("message_send", {"channel": "email", "body": "x", "recipient": "u"})

    monkeypatch.setenv("JARVIS_APPROVAL_DB", str(approvals_db))

    rc = main(["approvals-list"])
    out = capsys.readouterr().out

    assert rc == 0
    assert approval_id in out
    assert "message_send" in out


def test_main_approvals_dispatch_processes_approved_message_send(tmp_path, monkeypatch):
    approvals_db = tmp_path / "approvals.db"
    outbox = tmp_path / "outbox.jsonl"
    store = ApprovalStore(approvals_db)
    approval_id = store.request(
        "message_send",
        {
            "channel": "email",
            "recipient": "user@example.com",
            "subject": "Hi",
            "body": "hello",
        },
    )
    assert store.approve(approval_id)

    monkeypatch.setenv("JARVIS_APPROVAL_DB", str(approvals_db))
    monkeypatch.setenv("JARVIS_MESSAGE_OUTBOX", str(outbox))
    monkeypatch.setenv("JARVIS_MESSAGE_SEND_MODE", "dry_run")

    rc = main(["approvals-dispatch"])

    assert rc == 0
    assert outbox.exists()
    row = store.get(approval_id)
    assert row is not None
    assert row["status"] == "processed"


def test_main_approvals_approve_fails_for_stale_pending_after_auto_expiry(
    tmp_path,
    monkeypatch,
    capsys,
):
    approvals_db = tmp_path / "approvals.db"
    store = ApprovalStore(approvals_db)
    stale_id = store.request(
        "message_send",
        {"channel": "email", "recipient": "u", "body": "x"},
        created_ts=time.time() - 3600,
    )

    monkeypatch.setenv("JARVIS_APPROVAL_DB", str(approvals_db))
    monkeypatch.setenv("JARVIS_APPROVALS_TTL_SECONDS", "300")

    rc = main(["approvals-approve", stale_id])
    out = capsys.readouterr().out

    assert rc == 1
    assert "not found or not pending" in out
    row = store.get(stale_id)
    assert row is not None
    assert row["status"] == "rejected"
    assert "expired" in row["decision_reason"]


def test_main_approvals_dispatch_respects_max_per_run(tmp_path, monkeypatch):
    approvals_db = tmp_path / "approvals.db"
    outbox = tmp_path / "outbox.jsonl"
    store = ApprovalStore(approvals_db)

    first = store.request(
        "message_send",
        {"channel": "email", "recipient": "a@example.com", "body": "one"},
    )
    second = store.request(
        "message_send",
        {"channel": "email", "recipient": "b@example.com", "body": "two"},
    )
    assert store.approve(first)
    assert store.approve(second)

    monkeypatch.setenv("JARVIS_APPROVAL_DB", str(approvals_db))
    monkeypatch.setenv("JARVIS_MESSAGE_OUTBOX", str(outbox))
    monkeypatch.setenv("JARVIS_MESSAGE_SEND_MODE", "dry_run")
    monkeypatch.setenv("JARVIS_APPROVALS_DISPATCH_MAX_PER_RUN", "1")

    rc = main(["approvals-dispatch"])

    assert rc == 0
    first_row = store.get(first)
    second_row = store.get(second)
    assert first_row is not None
    assert second_row is not None
    assert first_row["status"] == "processed"
    assert second_row["status"] == "approved"


def test_main_approvals_dispatch_respects_cooldown(tmp_path, monkeypatch, capsys):
    approvals_db = tmp_path / "approvals.db"
    outbox = tmp_path / "outbox.jsonl"
    store = ApprovalStore(approvals_db)

    previous = store.request(
        "message_send",
        {"channel": "email", "recipient": "x@example.com", "body": "prev"},
    )
    assert store.approve(previous)
    assert store.mark_dispatched(previous, success=True, result={"status": "dry_run_sent"})

    queued = store.request(
        "message_send",
        {"channel": "email", "recipient": "y@example.com", "body": "next"},
    )
    assert store.approve(queued)

    monkeypatch.setenv("JARVIS_APPROVAL_DB", str(approvals_db))
    monkeypatch.setenv("JARVIS_MESSAGE_OUTBOX", str(outbox))
    monkeypatch.setenv("JARVIS_MESSAGE_SEND_MODE", "dry_run")
    monkeypatch.setenv("JARVIS_APPROVALS_DISPATCH_COOLDOWN_SECONDS", "3600")

    rc = main(["approvals-dispatch"])
    out = capsys.readouterr().out

    assert rc == 0
    assert "cooldown active" in out.lower()
    queued_row = store.get(queued)
    assert queued_row is not None
    assert queued_row["status"] == "approved"


def test_main_approvals_dispatch_respects_per_kind_cooldown(
    tmp_path,
    monkeypatch,
    capsys,
):
    approvals_db = tmp_path / "approvals.db"
    outbox = tmp_path / "outbox.jsonl"
    store = ApprovalStore(approvals_db)

    previous = store.request(
        "message_send",
        {"channel": "email", "recipient": "x@example.com", "body": "prev"},
    )
    assert store.approve(previous)
    assert store.mark_dispatched(previous, success=True, result={"status": "dry_run_sent"})

    queued = store.request(
        "message_send",
        {"channel": "email", "recipient": "y@example.com", "body": "next"},
    )
    assert store.approve(queued)

    monkeypatch.setenv("JARVIS_APPROVAL_DB", str(approvals_db))
    monkeypatch.setenv("JARVIS_MESSAGE_OUTBOX", str(outbox))
    monkeypatch.setenv("JARVIS_MESSAGE_SEND_MODE", "dry_run")
    monkeypatch.setenv("JARVIS_APPROVALS_DISPATCH_COOLDOWN_SECONDS", "0")
    monkeypatch.setenv("JARVIS_APPROVALS_DISPATCH_COOLDOWN_BY_KIND", "message_send:3600")

    rc = main(["approvals-dispatch"])
    out = capsys.readouterr().out

    assert rc == 0
    assert "per-kind" in out.lower()
    queued_row = store.get(queued)
    assert queued_row is not None
    assert queued_row["status"] == "approved"


def test_main_approvals_api_invokes_server_entrypoint(monkeypatch):
    called = {"host": None, "port": None}

    def _fake_api(host=None, port=None):
        called["host"] = host
        called["port"] = port
        return 0

    monkeypatch.setattr("jarvis.__main__._approvals_api", _fake_api)

    rc = main(["approvals-api", "127.0.0.1", "9091"])

    assert rc == 0
    assert called["host"] == "127.0.0.1"
    assert called["port"] == 9091


def test_approvals_api_falls_back_to_next_port_when_requested_port_busy(
    monkeypatch,
    capsys,
):
    class _FakeServer:
        def __init__(self):
            self.closed = False

        def serve_forever(self):
            raise KeyboardInterrupt

        def server_close(self):
            self.closed = True

    attempts = []
    fake_server = _FakeServer()

    def _fake_factory(config, host, port):
        attempts.append(port)
        if port == 8080:
            raise OSError(errno.EADDRINUSE, "Address already in use")
        return fake_server

    monkeypatch.setattr("jarvis.__main__.create_approval_api_server", _fake_factory)

    rc = main(["approvals-api", "127.0.0.1", "8080"])
    out = capsys.readouterr().out

    assert rc == 0
    assert attempts == [8080, 8081]
    assert "Requested port 8080 busy" in out
    assert "http://127.0.0.1:8081" in out
    assert fake_server.closed is True


def test_approvals_api_returns_error_when_no_fallback_port_is_available(
    monkeypatch,
    capsys,
):
    attempts = []

    def _always_busy(config, host, port):
        attempts.append(port)
        raise OSError(errno.EADDRINUSE, "Address already in use")

    monkeypatch.setattr("jarvis.__main__.create_approval_api_server", _always_busy)

    rc = main(["approvals-api", "127.0.0.1", "8080"])
    out = capsys.readouterr().out

    assert rc == 1
    assert attempts == list(range(8080, 8090))
    assert "ports 8080-8089 are in use" in out


def test_approvals_seed_creates_demo_approvals(tmp_path, monkeypatch, capsys):
    approvals_db = tmp_path / "approvals.db"
    monkeypatch.setenv("JARVIS_APPROVAL_DB", str(approvals_db))

    rc = main(["approvals-seed", "2"])
    out = capsys.readouterr().out

    assert rc == 0
    assert "Created approval 1/" in out
    assert "Created approval 2/" in out
    assert "Open web UI to review and approve" in out

    from jarvis.approval import ApprovalStore
    store = ApprovalStore(approvals_db)
    pending = store.list_pending(limit=100)
    assert len(pending) == 2
    assert pending[0]["kind"] == "message_send"
    assert pending[1]["kind"] == "message_send"


def test_approvals_seed_default_count_is_three(tmp_path, monkeypatch, capsys):
    approvals_db = tmp_path / "approvals.db"
    monkeypatch.setenv("JARVIS_APPROVAL_DB", str(approvals_db))

    rc = main(["approvals-seed"])
    out = capsys.readouterr().out

    assert rc == 0
    assert "Created approval 1/" in out
    assert "Created approval 2/" in out
    assert "Created approval 3/" in out

    from jarvis.approval import ApprovalStore
    store = ApprovalStore(approvals_db)
    pending = store.list_pending(limit=100)
    assert len(pending) == 3


def test_main_events_stats_prints_counts(tmp_path, monkeypatch, capsys):
    bus_db = tmp_path / "events.db"
    bus = EventBus(bus_db)
    bus.emit(Event(kind="calendar_event", source="calendar", payload={"x": 1}))
    bus.emit(Event(kind="rss_article", source="rss_demo", payload={"x": 2}))

    monkeypatch.setenv("JARVIS_EVENT_BUS_DB", str(bus_db))

    rc = main(["events-stats"])
    out = capsys.readouterr().out.strip()

    assert rc == 0
    data = json.loads(out)
    assert data["total"] == 2
    assert data["calendar_event"] == 1
    assert data["rss_article"] == 1


def test_main_monitors_status_prints_configured_monitors(tmp_path, monkeypatch, capsys):
    bus_db = tmp_path / "events.db"
    calendar_path = tmp_path / "calendar.ics"
    dropzone_dir = tmp_path / "dropzone"

    monkeypatch.setenv("JARVIS_EVENT_BUS_DB", str(bus_db))
    monkeypatch.setenv("JARVIS_CALENDAR_ICS", str(calendar_path))
    monkeypatch.setenv("JARVIS_DROPZONE_DIR", str(dropzone_dir))

    rc = main(["monitors-status"])
    out = capsys.readouterr().out.strip()

    assert rc == 0
    data = json.loads(out)
    assert data["monitors"] == 4
    assert "calendar" in data["monitor_status"]
    assert "filesystem" in data["monitor_status"]


def test_main_events_list_unprocessed(tmp_path, monkeypatch, capsys):
    bus_db = tmp_path / "events.db"
    bus = EventBus(bus_db)
    first = Event(kind="calendar_event", source="calendar", payload={"title": "A"})
    second = Event(kind="calendar_event", source="calendar", payload={"title": "B"})
    bus.emit(first)
    bus.emit(second)
    bus.mark_processed(first.id)

    monkeypatch.setenv("JARVIS_EVENT_BUS_DB", str(bus_db))

    rc = main(["events-list", "10", "--unprocessed"])
    lines = [line for line in capsys.readouterr().out.splitlines() if line.strip()]

    assert rc == 0
    assert len(lines) == 1
    data = json.loads(lines[0])
    assert data["id"] == second.id
    assert data["processed"] is False


def test_main_monitor_run_once_uses_configured_monitors(tmp_path, monkeypatch, capsys):
    bus_db = tmp_path / "events.db"
    calendar = tmp_path / "calendar.ics"
    dropzone = tmp_path / "dropzone"
    dropzone.mkdir()

    monkeypatch.setenv("JARVIS_EVENT_BUS_DB", str(bus_db))
    monkeypatch.setenv("JARVIS_CALENDAR_ICS", str(calendar))
    monkeypatch.setenv("JARVIS_DROPZONE_DIR", str(dropzone))
    monkeypatch.setenv("JARVIS_RSS_FEED_URL", "")

    rc = main(["monitor-run-once"])
    out = capsys.readouterr().out.strip()

    assert rc == 0
    data = json.loads(out)
    assert data["monitors"] == 2
    assert data["rss_enabled"] is False


def test_main_webhook_listen_invokes_entrypoint(monkeypatch):
    called = {"source": None, "host": None, "port": None}

    def _fake_webhook(source_name=None, host=None, port=None):
        called["source"] = source_name
        called["host"] = host
        called["port"] = port
        return 0

    monkeypatch.setattr("jarvis.__main__._webhook_listen", _fake_webhook)

    rc = main(["webhook-listen", "github", "127.0.0.1", "9020"])

    assert rc == 0
    assert called["source"] == "github"
    assert called["host"] == "127.0.0.1"
    assert called["port"] == 9020


def test_main_vision_listen_invokes_entrypoint(monkeypatch):
    called = {"source": None, "host": None, "port": None}

    def _fake_vision(source_name=None, host=None, port=None):
        called["source"] = source_name
        called["host"] = host
        called["port"] = port
        return 0

    monkeypatch.setattr("jarvis.__main__._vision_listen", _fake_vision)

    rc = main(["vision-listen", "iphone", "127.0.0.1", "9030"])

    assert rc == 0
    assert called["source"] == "iphone"
    assert called["host"] == "127.0.0.1"
    assert called["port"] == 9030


def test_main_vision_shortcut_template_default_url(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("JARVIS_EVENT_BUS_DB", str(tmp_path / "events.db"))
    monkeypatch.setenv("JARVIS_APPROVAL_DB", str(tmp_path / "approvals.db"))
    monkeypatch.setenv("JARVIS_AUDIT_DB", str(tmp_path / "audit.db"))
    monkeypatch.setenv("JARVIS_VISION_HOST", "127.0.0.1")
    monkeypatch.setenv("JARVIS_VISION_PORT", "9021")

    rc = main(["vision-shortcut-template"])
    out = capsys.readouterr().out

    assert rc == 0
    data = json.loads(out)
    assert data["request"]["url"] == "http://127.0.0.1:9021/frame"
    assert data["request"]["method"] == "POST"


def test_main_vision_shortcut_template_with_secret(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("JARVIS_EVENT_BUS_DB", str(tmp_path / "events.db"))
    monkeypatch.setenv("JARVIS_APPROVAL_DB", str(tmp_path / "approvals.db"))
    monkeypatch.setenv("JARVIS_AUDIT_DB", str(tmp_path / "audit.db"))
    monkeypatch.setenv("JARVIS_VISION_SECRET", "secret")

    rc = main(["vision-shortcut-template", "http://127.0.0.1:9999/frame"])
    out = capsys.readouterr().out

    assert rc == 0
    data = json.loads(out)
    assert data["request"]["url"] == "http://127.0.0.1:9999/frame"
    assert data["request"]["headers"]["X-Jarvis-Signature"].startswith("sha256=")


def test_main_vision_shortcut_guide_default_url(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("JARVIS_EVENT_BUS_DB", str(tmp_path / "events.db"))
    monkeypatch.setenv("JARVIS_APPROVAL_DB", str(tmp_path / "approvals.db"))
    monkeypatch.setenv("JARVIS_AUDIT_DB", str(tmp_path / "audit.db"))
    monkeypatch.setenv("JARVIS_VISION_HOST", "127.0.0.1")
    monkeypatch.setenv("JARVIS_VISION_PORT", "9021")

    rc = main(["vision-shortcut-guide"])
    out = capsys.readouterr().out

    assert rc == 0
    data = json.loads(out)
    assert data["url"] == "http://127.0.0.1:9021/frame"
    assert data["title"] == "iPhone Shortcuts Vision Upload Guide"


def test_main_vision_shortcut_guide_includes_signature_when_secret_set(
    tmp_path,
    monkeypatch,
    capsys,
):
    monkeypatch.setenv("JARVIS_EVENT_BUS_DB", str(tmp_path / "events.db"))
    monkeypatch.setenv("JARVIS_APPROVAL_DB", str(tmp_path / "approvals.db"))
    monkeypatch.setenv("JARVIS_AUDIT_DB", str(tmp_path / "audit.db"))
    monkeypatch.setenv("JARVIS_VISION_SECRET", "secret")

    rc = main(["vision-shortcut-guide", "http://127.0.0.1:9999/frame"])
    out = capsys.readouterr().out

    assert rc == 0
    data = json.loads(out)
    titles = [step["title"] for step in data["steps"]]
    assert data["url"] == "http://127.0.0.1:9999/frame"
    assert data["signing_enabled"] is True
    assert "Enable Signature" in titles



# ---------------------------------------------------------------------------
# vision-analyze CLI tests
# ---------------------------------------------------------------------------

def test_main_vision_analyze_missing_arg(capsys):
    rc = main(["vision-analyze"])
    out = capsys.readouterr().out
    assert rc == 1
    data = json.loads(out)
    assert data["ok"] is False
    assert data["error"] == "missing_image_arg"


def test_main_vision_analyze_file_not_found(tmp_path, capsys):
    rc = main(["vision-analyze", str(tmp_path / "nonexistent.jpg")])
    out = capsys.readouterr().out
    assert rc == 1
    data = json.loads(out)
    assert data["ok"] is False
    assert data["error"] == "image_file_not_found"


def test_main_vision_analyze_solid_color_image(tmp_path, capsys):
    import io
    from PIL import Image
    img = Image.new("RGB", (50, 50), (30, 30, 210))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    p = tmp_path / "blue.jpg"
    p.write_bytes(buf.getvalue())

    rc = main(["vision-analyze", str(p)])
    out = capsys.readouterr().out
    assert rc == 0
    data = json.loads(out)
    assert data["ok"] is True
    assert isinstance(data["faces"], list)
    assert isinstance(data["colors"], list)
    assert data["face_count"] == len(data["faces"])
    assert data["colors"][0]["name"] == "blue"


def test_main_vision_analyze_no_colors_flag(tmp_path, capsys):
    import io
    from PIL import Image
    img = Image.new("RGB", (50, 50), (220, 40, 40))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    p = tmp_path / "red.jpg"
    p.write_bytes(buf.getvalue())

    rc = main(["vision-analyze", str(p), "--no-colors"])
    out = capsys.readouterr().out
    assert rc == 0
    data = json.loads(out)
    assert data["ok"] is True
    assert data["colors"] == []


def test_main_vision_analyze_no_faces_flag(tmp_path, capsys):
    import io
    from PIL import Image
    img = Image.new("RGB", (50, 50), (30, 200, 30))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    p = tmp_path / "green.jpg"
    p.write_bytes(buf.getvalue())

    rc = main(["vision-analyze", str(p), "--no-faces"])
    out = capsys.readouterr().out
    assert rc == 0
    data = json.loads(out)
    assert data["ok"] is True
    assert data["faces"] == []


def test_main_vision_analyze_max_colors(tmp_path, capsys):
    import io
    from PIL import Image
    img = Image.new("RGB", (50, 50), (30, 30, 210))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    p = tmp_path / "blue2.jpg"
    p.write_bytes(buf.getvalue())

    rc = main(["vision-analyze", str(p), "--max-colors", "2"])
    out = capsys.readouterr().out
    assert rc == 0
    data = json.loads(out)
    assert len(data["colors"]) <= 2


def test_main_vision_analyze_max_colors_equals_syntax(tmp_path, capsys):
    import io
    from PIL import Image
    img = Image.new("RGB", (50, 50), (30, 30, 210))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    p = tmp_path / "blue3.jpg"
    p.write_bytes(buf.getvalue())

    rc = main(["vision-analyze", str(p), "--max-colors=1"])
    out = capsys.readouterr().out
    assert rc == 0
    data = json.loads(out)
    assert len(data["colors"]) <= 1


def test_main_vision_analyze_base64_input(capsys):
    import base64, io
    from PIL import Image
    img = Image.new("RGB", (50, 50), (220, 40, 40))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")

    rc = main(["vision-analyze", b64])
    out = capsys.readouterr().out
    assert rc == 0
    data = json.loads(out)
    assert data["ok"] is True
    assert data["colors"][0]["name"] == "red"


def test_main_vision_analyze_invalid_max_colors_value(tmp_path, capsys):
    import io
    from PIL import Image
    img = Image.new("RGB", (10, 10), (100, 100, 100))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    p = tmp_path / "gray.jpg"
    p.write_bytes(buf.getvalue())

    rc = main(["vision-analyze", str(p), "--max-colors", "abc"])
    out = capsys.readouterr().out
    assert rc == 1
    data = json.loads(out)
    assert data["ok"] is False
    assert data["error"] == "invalid_max_colors_value"


def test_main_vision_analyze_missing_max_colors_value(tmp_path, capsys):
    import io
    from PIL import Image
    img = Image.new("RGB", (10, 10), (100, 100, 100))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    p = tmp_path / "gray2.jpg"
    p.write_bytes(buf.getvalue())

    rc = main(["vision-analyze", str(p), "--max-colors"])
    out = capsys.readouterr().out
    assert rc == 1
    data = json.loads(out)
    assert data["ok"] is False
    assert data["error"] == "missing_max_colors_value"


def test_main_vision_analyze_missing_max_colors_value_equals_syntax(tmp_path, capsys):
    import io
    from PIL import Image
    img = Image.new("RGB", (10, 10), (100, 100, 100))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    p = tmp_path / "gray3.jpg"
    p.write_bytes(buf.getvalue())

    rc = main(["vision-analyze", str(p), "--max-colors="])
    out = capsys.readouterr().out
    assert rc == 1
    data = json.loads(out)
    assert data["ok"] is False
    assert data["error"] == "missing_max_colors_value"


def test_main_vision_self_test_end_to_end(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("JARVIS_EVENT_BUS_DB", str(tmp_path / "events.db"))
    monkeypatch.setenv("JARVIS_APPROVAL_DB", str(tmp_path / "approvals.db"))
    monkeypatch.setenv("JARVIS_AUDIT_DB", str(tmp_path / "audit.db"))
    monkeypatch.setenv("JARVIS_VISION_HOST", "127.0.0.1")
    monkeypatch.setenv("JARVIS_VISION_PORT", "9021")
    monkeypatch.setenv("JARVIS_VISION_SECRET", "")

    rc = main(["vision-self-test"])
    out = capsys.readouterr().out

    assert rc == 0
    data = json.loads(out)
    assert data["ok"] is True
    assert data["http_accepted"] is True
    assert data["emitted"] >= 1
    assert data["processed"] >= 1


def test_main_vision_self_test_multipart_mode(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("JARVIS_EVENT_BUS_DB", str(tmp_path / "events.db"))
    monkeypatch.setenv("JARVIS_APPROVAL_DB", str(tmp_path / "approvals.db"))
    monkeypatch.setenv("JARVIS_AUDIT_DB", str(tmp_path / "audit.db"))
    monkeypatch.setenv("JARVIS_VISION_SECRET", "")

    rc = main(["vision-self-test", "multipart"])
    out = capsys.readouterr().out

    assert rc == 0
    data = json.loads(out)
    assert data["ok"] is True
    assert data["mode"] == "multipart"


def test_main_vision_self_test_binary_mode(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("JARVIS_EVENT_BUS_DB", str(tmp_path / "events.db"))
    monkeypatch.setenv("JARVIS_APPROVAL_DB", str(tmp_path / "approvals.db"))
    monkeypatch.setenv("JARVIS_AUDIT_DB", str(tmp_path / "audit.db"))
    monkeypatch.setenv("JARVIS_VISION_SECRET", "")

    rc = main(["vision-self-test", "binary"])
    out = capsys.readouterr().out

    assert rc == 0
    data = json.loads(out)
    assert data["ok"] is True
    assert data["mode"] == "binary"


def test_main_vision_self_test_invalid_mode(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("JARVIS_EVENT_BUS_DB", str(tmp_path / "events.db"))
    monkeypatch.setenv("JARVIS_APPROVAL_DB", str(tmp_path / "approvals.db"))
    monkeypatch.setenv("JARVIS_AUDIT_DB", str(tmp_path / "audit.db"))

    rc = main(["vision-self-test", "invalid"])
    out = capsys.readouterr().out

    assert rc == 1
    data = json.loads(out)
    assert data["ok"] is False
    assert data["error"] == "invalid_mode"


def test_main_vision_self_test_with_secret_enables_signing(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("JARVIS_EVENT_BUS_DB", str(tmp_path / "events.db"))
    monkeypatch.setenv("JARVIS_APPROVAL_DB", str(tmp_path / "approvals.db"))
    monkeypatch.setenv("JARVIS_AUDIT_DB", str(tmp_path / "audit.db"))
    monkeypatch.setenv("JARVIS_VISION_SECRET", "")

    rc = main(["vision-self-test", "json", "--with-secret"])
    out = capsys.readouterr().out

    assert rc == 0
    data = json.loads(out)
    assert data["ok"] is True
    assert data["signing_enabled"] is True
    assert data["ephemeral_secret_used"] is True


def test_main_vision_self_test_with_secret_flag_before_mode(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("JARVIS_EVENT_BUS_DB", str(tmp_path / "events.db"))
    monkeypatch.setenv("JARVIS_APPROVAL_DB", str(tmp_path / "approvals.db"))
    monkeypatch.setenv("JARVIS_AUDIT_DB", str(tmp_path / "audit.db"))

    rc = main(["vision-self-test", "--with-secret", "multipart"])
    out = capsys.readouterr().out

    assert rc == 0
    data = json.loads(out)
    assert data["ok"] is True
    assert data["mode"] == "multipart"
    assert data["signing_enabled"] is True


def test_main_vision_self_test_report_includes_diagnostics(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("JARVIS_EVENT_BUS_DB", str(tmp_path / "events.db"))
    monkeypatch.setenv("JARVIS_APPROVAL_DB", str(tmp_path / "approvals.db"))
    monkeypatch.setenv("JARVIS_AUDIT_DB", str(tmp_path / "audit.db"))
    monkeypatch.setenv("JARVIS_VISION_SECRET", "")

    rc = main(["vision-self-test", "json", "--report"])
    out = capsys.readouterr().out

    assert rc == 0
    data = json.loads(out)
    assert data["ok"] is True
    assert "report" in data
    report = data["report"]
    assert report["frame_id"].startswith("self-test-")
    assert "timings_ms" in report
    assert "http_post" in report["timings_ms"]
    assert "items" in report
    assert isinstance(report["items"], list)


def test_main_vision_self_test_report_and_with_secret_flags_any_order(
    tmp_path,
    monkeypatch,
    capsys,
):
    monkeypatch.setenv("JARVIS_EVENT_BUS_DB", str(tmp_path / "events.db"))
    monkeypatch.setenv("JARVIS_APPROVAL_DB", str(tmp_path / "approvals.db"))
    monkeypatch.setenv("JARVIS_AUDIT_DB", str(tmp_path / "audit.db"))
    monkeypatch.setenv("JARVIS_VISION_SECRET", "")

    rc = main(["vision-self-test", "--report", "--with-secret", "binary"])
    out = capsys.readouterr().out

    assert rc == 0
    data = json.loads(out)
    assert data["ok"] is True
    assert data["mode"] == "binary"
    assert data["signing_enabled"] is True
    assert data["ephemeral_secret_used"] is True
    assert "report" in data


def test_main_vision_self_test_all_mode_runs_all_ingest_paths(
    tmp_path,
    monkeypatch,
    capsys,
):
    monkeypatch.setenv("JARVIS_EVENT_BUS_DB", str(tmp_path / "events.db"))
    monkeypatch.setenv("JARVIS_APPROVAL_DB", str(tmp_path / "approvals.db"))
    monkeypatch.setenv("JARVIS_AUDIT_DB", str(tmp_path / "audit.db"))

    rc = main(["vision-self-test", "all"])
    out = capsys.readouterr().out

    assert rc == 0
    data = json.loads(out)
    assert data["ok"] is True
    assert data["mode"] == "all"
    assert len(data["results"]) == 3
    modes = [item["mode"] for item in data["results"]]
    assert modes == ["json", "multipart", "binary"]
    assert all(item["ok"] is True for item in data["results"])


def test_main_vision_self_test_all_mode_with_report_has_totals(
    tmp_path,
    monkeypatch,
    capsys,
):
    monkeypatch.setenv("JARVIS_EVENT_BUS_DB", str(tmp_path / "events.db"))
    monkeypatch.setenv("JARVIS_APPROVAL_DB", str(tmp_path / "approvals.db"))
    monkeypatch.setenv("JARVIS_AUDIT_DB", str(tmp_path / "audit.db"))

    rc = main(["vision-self-test", "all", "--report"])
    out = capsys.readouterr().out

    assert rc == 0
    data = json.loads(out)
    assert data["ok"] is True
    assert "report" in data
    assert data["report"]["modes_run"] == ["json", "multipart", "binary"]
    assert data["report"]["total_processed"] >= 3
    assert data["report"]["total_approvals_created"] >= 3


def test_main_vision_self_test_all_mode_fail_fast_flag_reflected(
    tmp_path,
    monkeypatch,
    capsys,
):
    monkeypatch.setenv("JARVIS_EVENT_BUS_DB", str(tmp_path / "events.db"))
    monkeypatch.setenv("JARVIS_APPROVAL_DB", str(tmp_path / "approvals.db"))
    monkeypatch.setenv("JARVIS_AUDIT_DB", str(tmp_path / "audit.db"))

    rc = main(["vision-self-test", "all", "--fail-fast"])
    out = capsys.readouterr().out

    assert rc == 0
    data = json.loads(out)
    assert data["ok"] is True
    assert data["mode"] == "all"
    assert data["fail_fast"] is True
    assert len(data["results"]) == 3


def test_main_vision_self_test_all_mode_fail_fast_stops_after_first_failure(
    tmp_path,
    monkeypatch,
    capsys,
):
    monkeypatch.setenv("JARVIS_EVENT_BUS_DB", str(tmp_path / "events.db"))
    monkeypatch.setenv("JARVIS_APPROVAL_DB", str(tmp_path / "approvals.db"))
    monkeypatch.setenv("JARVIS_AUDIT_DB", str(tmp_path / "audit.db"))

    real_urlopen = __import__("jarvis.__main__", fromlist=["urllib"]).urllib.request.urlopen
    calls = {"n": 0}

    def _fake_urlopen(request, timeout=10):
        calls["n"] += 1
        if calls["n"] == 2:
            raise RuntimeError("forced failure")
        return real_urlopen(request, timeout=timeout)

    monkeypatch.setattr("jarvis.__main__.urllib.request.urlopen", _fake_urlopen)

    rc = main(["vision-self-test", "all", "--fail-fast", "--report"])
    out = capsys.readouterr().out

    assert rc == 2
    data = json.loads(out)
    assert data["ok"] is False
    assert data["fail_fast"] is True
    assert len(data["results"]) == 2
    assert data["results"][0]["mode"] == "json"
    assert data["results"][1]["mode"] == "multipart"
    assert data["results"][1]["ok"] is False
    assert data["report"]["modes_run"] == ["json", "multipart"]


def test_main_vision_self_test_all_mode_max_modes_limits_execution(
    tmp_path,
    monkeypatch,
    capsys,
):
    monkeypatch.setenv("JARVIS_EVENT_BUS_DB", str(tmp_path / "events.db"))
    monkeypatch.setenv("JARVIS_APPROVAL_DB", str(tmp_path / "approvals.db"))
    monkeypatch.setenv("JARVIS_AUDIT_DB", str(tmp_path / "audit.db"))

    rc = main(["vision-self-test", "all", "--max-modes", "2", "--report"])
    out = capsys.readouterr().out

    assert rc == 0
    data = json.loads(out)
    assert data["ok"] is True
    assert data["mode"] == "all"
    assert data["max_modes_requested"] == 2
    assert len(data["results"]) == 2
    assert [item["mode"] for item in data["results"]] == ["json", "multipart"]
    assert data["report"]["modes_run"] == ["json", "multipart"]


def test_main_vision_self_test_all_mode_max_modes_equals_syntax(
    tmp_path,
    monkeypatch,
    capsys,
):
    monkeypatch.setenv("JARVIS_EVENT_BUS_DB", str(tmp_path / "events.db"))
    monkeypatch.setenv("JARVIS_APPROVAL_DB", str(tmp_path / "approvals.db"))
    monkeypatch.setenv("JARVIS_AUDIT_DB", str(tmp_path / "audit.db"))

    rc = main(["vision-self-test", "all", "--max-modes=1"])
    out = capsys.readouterr().out

    assert rc == 0
    data = json.loads(out)
    assert data["ok"] is True
    assert data["max_modes_requested"] == 1
    assert len(data["results"]) == 1
    assert data["results"][0]["mode"] == "json"


def test_main_vision_self_test_all_mode_rejects_invalid_max_modes(
    tmp_path,
    monkeypatch,
    capsys,
):
    monkeypatch.setenv("JARVIS_EVENT_BUS_DB", str(tmp_path / "events.db"))
    monkeypatch.setenv("JARVIS_APPROVAL_DB", str(tmp_path / "approvals.db"))
    monkeypatch.setenv("JARVIS_AUDIT_DB", str(tmp_path / "audit.db"))

    rc = main(["vision-self-test", "all", "--max-modes", "0"])
    out = capsys.readouterr().out

    assert rc == 1
    data = json.loads(out)
    assert data["ok"] is False
    assert data["error"] == "invalid_max_modes_value"


def test_main_vision_self_test_all_mode_missing_max_modes_value_equals_syntax(
    tmp_path,
    monkeypatch,
    capsys,
):
    monkeypatch.setenv("JARVIS_EVENT_BUS_DB", str(tmp_path / "events.db"))
    monkeypatch.setenv("JARVIS_APPROVAL_DB", str(tmp_path / "approvals.db"))
    monkeypatch.setenv("JARVIS_AUDIT_DB", str(tmp_path / "audit.db"))

    rc = main(["vision-self-test", "all", "--max-modes="])
    out = capsys.readouterr().out

    assert rc == 1
    data = json.loads(out)
    assert data["ok"] is False
    assert data["error"] == "missing_max_modes_value"


def test_main_vision_self_test_all_mode_modes_limits_selection(
    tmp_path,
    monkeypatch,
    capsys,
):
    monkeypatch.setenv("JARVIS_EVENT_BUS_DB", str(tmp_path / "events.db"))
    monkeypatch.setenv("JARVIS_APPROVAL_DB", str(tmp_path / "approvals.db"))
    monkeypatch.setenv("JARVIS_AUDIT_DB", str(tmp_path / "audit.db"))

    rc = main(["vision-self-test", "all", "--modes", "binary,json", "--report"])
    out = capsys.readouterr().out

    assert rc == 0
    data = json.loads(out)
    assert data["ok"] is True
    assert data["modes_requested"] == ["binary", "json"]
    assert [item["mode"] for item in data["results"]] == ["binary", "json"]
    assert data["report"]["modes_run"] == ["binary", "json"]


def test_main_vision_self_test_all_mode_modes_equals_syntax(
    tmp_path,
    monkeypatch,
    capsys,
):
    monkeypatch.setenv("JARVIS_EVENT_BUS_DB", str(tmp_path / "events.db"))
    monkeypatch.setenv("JARVIS_APPROVAL_DB", str(tmp_path / "approvals.db"))
    monkeypatch.setenv("JARVIS_AUDIT_DB", str(tmp_path / "audit.db"))

    rc = main(["vision-self-test", "all", "--modes=json,multipart"])
    out = capsys.readouterr().out

    assert rc == 0
    data = json.loads(out)
    assert data["ok"] is True
    assert data["modes_requested"] == ["json", "multipart"]
    assert [item["mode"] for item in data["results"]] == ["json", "multipart"]


def test_main_vision_self_test_rejects_invalid_modes_value(
    tmp_path,
    monkeypatch,
    capsys,
):
    monkeypatch.setenv("JARVIS_EVENT_BUS_DB", str(tmp_path / "events.db"))
    monkeypatch.setenv("JARVIS_APPROVAL_DB", str(tmp_path / "approvals.db"))
    monkeypatch.setenv("JARVIS_AUDIT_DB", str(tmp_path / "audit.db"))

    rc = main(["vision-self-test", "all", "--modes", "json,unknown"])
    out = capsys.readouterr().out

    assert rc == 1
    data = json.loads(out)
    assert data["ok"] is False
    assert data["error"] == "invalid_modes_value"


def test_main_vision_self_test_rejects_missing_modes_value_equals_syntax(
    tmp_path,
    monkeypatch,
    capsys,
):
    monkeypatch.setenv("JARVIS_EVENT_BUS_DB", str(tmp_path / "events.db"))
    monkeypatch.setenv("JARVIS_APPROVAL_DB", str(tmp_path / "approvals.db"))
    monkeypatch.setenv("JARVIS_AUDIT_DB", str(tmp_path / "audit.db"))

    rc = main(["vision-self-test", "all", "--modes="])
    out = capsys.readouterr().out

    assert rc == 1
    data = json.loads(out)
    assert data["ok"] is False
    assert data["error"] == "missing_modes_value"


def test_main_vision_self_test_rejects_modes_without_all(
    tmp_path,
    monkeypatch,
    capsys,
):
    monkeypatch.setenv("JARVIS_EVENT_BUS_DB", str(tmp_path / "events.db"))
    monkeypatch.setenv("JARVIS_APPROVAL_DB", str(tmp_path / "approvals.db"))
    monkeypatch.setenv("JARVIS_AUDIT_DB", str(tmp_path / "audit.db"))

    rc = main(["vision-self-test", "json", "--modes", "json,multipart"])
    out = capsys.readouterr().out

    assert rc == 1
    data = json.loads(out)
    assert data["ok"] is False
    assert data["error"] == "modes_requires_all_mode"


def test_main_vision_self_test_writes_output_file_for_single_mode(
    tmp_path,
    monkeypatch,
    capsys,
):
    monkeypatch.setenv("JARVIS_EVENT_BUS_DB", str(tmp_path / "events.db"))
    monkeypatch.setenv("JARVIS_APPROVAL_DB", str(tmp_path / "approvals.db"))
    monkeypatch.setenv("JARVIS_AUDIT_DB", str(tmp_path / "audit.db"))

    out_file = tmp_path / "artifacts" / "vision.json"
    rc = main(["vision-self-test", "json", "--output-file", str(out_file)])
    out = capsys.readouterr().out

    assert rc == 0
    data = json.loads(out)
    assert data["ok"] is True
    assert data["output_file"] == str(out_file)
    assert out_file.exists()
    persisted = json.loads(out_file.read_text(encoding="utf-8"))
    assert persisted["mode"] == "json"


def test_main_vision_self_test_writes_output_file_for_all_mode(
    tmp_path,
    monkeypatch,
    capsys,
):
    monkeypatch.setenv("JARVIS_EVENT_BUS_DB", str(tmp_path / "events.db"))
    monkeypatch.setenv("JARVIS_APPROVAL_DB", str(tmp_path / "approvals.db"))
    monkeypatch.setenv("JARVIS_AUDIT_DB", str(tmp_path / "audit.db"))

    out_file = tmp_path / "artifacts" / "vision-all.json"
    rc = main(
        [
            "vision-self-test",
            "all",
            "--modes",
            "json,binary",
            "--output-file",
            str(out_file),
        ]
    )
    out = capsys.readouterr().out

    assert rc == 0
    data = json.loads(out)
    assert data["ok"] is True
    assert data["mode"] == "all"
    assert data["output_file"] == str(out_file)
    persisted = json.loads(out_file.read_text(encoding="utf-8"))
    assert persisted["mode"] == "all"
    assert [item["mode"] for item in persisted["results"]] == ["json", "binary"]


def test_main_vision_self_test_rejects_missing_output_file_value(
    tmp_path,
    monkeypatch,
    capsys,
):
    monkeypatch.setenv("JARVIS_EVENT_BUS_DB", str(tmp_path / "events.db"))
    monkeypatch.setenv("JARVIS_APPROVAL_DB", str(tmp_path / "approvals.db"))
    monkeypatch.setenv("JARVIS_AUDIT_DB", str(tmp_path / "audit.db"))

    rc = main(["vision-self-test", "json", "--output-file"])
    out = capsys.readouterr().out

    assert rc == 1
    data = json.loads(out)
    assert data["ok"] is False
    assert data["error"] == "missing_output_file_value"


def test_main_vision_self_test_output_format_jsonl_appends(
    tmp_path,
    monkeypatch,
    capsys,
):
    monkeypatch.setenv("JARVIS_EVENT_BUS_DB", str(tmp_path / "events.db"))
    monkeypatch.setenv("JARVIS_APPROVAL_DB", str(tmp_path / "approvals.db"))
    monkeypatch.setenv("JARVIS_AUDIT_DB", str(tmp_path / "audit.db"))

    out_file = tmp_path / "artifacts" / "vision.jsonl"
    rc1 = main(
        [
            "vision-self-test",
            "json",
            "--output-file",
            str(out_file),
            "--output-format",
            "jsonl",
        ]
    )
    first = json.loads(capsys.readouterr().out)

    rc2 = main(
        [
            "vision-self-test",
            "binary",
            "--output-file",
            str(out_file),
            "--output-format",
            "jsonl",
        ]
    )
    second = json.loads(capsys.readouterr().out)

    assert rc1 == 0
    assert rc2 == 0
    assert first["output_format"] == "jsonl"
    assert second["output_format"] == "jsonl"

    lines = [line for line in out_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(lines) == 2
    row1 = json.loads(lines[0])
    row2 = json.loads(lines[1])
    assert row1["mode"] == "json"
    assert row2["mode"] == "binary"


def test_main_vision_self_test_rejects_missing_output_format_value(
    tmp_path,
    monkeypatch,
    capsys,
):
    monkeypatch.setenv("JARVIS_EVENT_BUS_DB", str(tmp_path / "events.db"))
    monkeypatch.setenv("JARVIS_APPROVAL_DB", str(tmp_path / "approvals.db"))
    monkeypatch.setenv("JARVIS_AUDIT_DB", str(tmp_path / "audit.db"))

    rc = main(["vision-self-test", "json", "--output-format"])
    out = capsys.readouterr().out

    assert rc == 1
    data = json.loads(out)
    assert data["ok"] is False
    assert data["error"] == "missing_output_format_value"


def test_main_vision_self_test_rejects_invalid_output_format(
    tmp_path,
    monkeypatch,
    capsys,
):
    monkeypatch.setenv("JARVIS_EVENT_BUS_DB", str(tmp_path / "events.db"))
    monkeypatch.setenv("JARVIS_APPROVAL_DB", str(tmp_path / "approvals.db"))
    monkeypatch.setenv("JARVIS_AUDIT_DB", str(tmp_path / "audit.db"))

    rc = main(["vision-self-test", "json", "--output-format", "xml"])
    out = capsys.readouterr().out

    assert rc == 1
    data = json.loads(out)
    assert data["ok"] is False
    assert data["error"] == "invalid_output_format"


def test_main_vision_self_test_summary_reports_counts_and_timings(
    tmp_path,
    monkeypatch,
    capsys,
):
    monkeypatch.setenv("JARVIS_EVENT_BUS_DB", str(tmp_path / "events.db"))
    monkeypatch.setenv("JARVIS_APPROVAL_DB", str(tmp_path / "approvals.db"))
    monkeypatch.setenv("JARVIS_AUDIT_DB", str(tmp_path / "audit.db"))

    jsonl_file = tmp_path / "artifacts" / "history.jsonl"
    assert main(
        [
            "vision-self-test",
            "json",
            "--report",
            "--output-file",
            str(jsonl_file),
            "--output-format",
            "jsonl",
        ]
    ) == 0
    capsys.readouterr()
    assert main(
        [
            "vision-self-test",
            "binary",
            "--report",
            "--output-file",
            str(jsonl_file),
            "--output-format",
            "jsonl",
        ]
    ) == 0
    capsys.readouterr()

    rc = main(["vision-self-test-summary", str(jsonl_file)])
    out = capsys.readouterr().out

    assert rc == 0
    data = json.loads(out)
    assert data["ok"] is True
    assert data["ema_alpha"] == 0.3
    assert data["total_runs"] == 2
    assert data["scanned_lines"] == 2
    assert data["pass_count"] == 2
    assert data["fail_count"] == 0
    assert data["invalid_line_rate"] == 0.0
    assert data["invalid_line_rate_ema"] == 0.0
    assert data["invalid_line_rate_previous_window"] is None
    assert data["invalid_line_rate_delta"] is None
    assert data["mode_counts"]["json"] == 1
    assert data["mode_counts"]["binary"] == 1
    assert data["timing_averages_ms"]["http_post"] is not None
    assert data["timing_percentiles_ms"]["http_post"]["p50"] is not None
    assert data["timing_percentiles_ms"]["http_post"]["p95"] is not None


def test_main_vision_self_test_summary_reports_percentiles_for_known_history(tmp_path, capsys):
    path = tmp_path / "known-history.jsonl"
    rows = [
        {
            "ok": True,
            "mode": "json",
            "report": {
                "timings_ms": {
                    "http_post": 10,
                    "drain_monitor_queue": 1,
                    "process_automation": 100,
                }
            },
        },
        {
            "ok": True,
            "mode": "json",
            "report": {
                "timings_ms": {
                    "http_post": 30,
                    "drain_monitor_queue": 3,
                    "process_automation": 300,
                }
            },
        },
        {
            "ok": True,
            "mode": "json",
            "report": {
                "timings_ms": {
                    "http_post": 50,
                    "drain_monitor_queue": 5,
                    "process_automation": 500,
                }
            },
        },
        {
            "ok": True,
            "mode": "json",
            "report": {
                "timings_ms": {
                    "http_post": 70,
                    "drain_monitor_queue": 7,
                    "process_automation": 700,
                }
            },
        },
    ]
    path.write_text("\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n", encoding="utf-8")

    rc = main(["vision-self-test-summary", str(path)])
    out = capsys.readouterr().out

    assert rc == 0
    data = json.loads(out)
    assert data["ok"] is True
    assert data["total_runs"] == 4
    assert data["scanned_lines"] == 4
    assert data["timing_averages_ms"]["http_post"] == 40.0
    assert data["invalid_line_rate"] == 0.0
    assert data["timing_percentiles_ms"]["http_post"]["p50"] == 40.0
    assert data["timing_percentiles_ms"]["http_post"]["p95"] == 67.0
    assert data["timing_percentiles_ms"]["drain_monitor_queue"]["p50"] == 4.0
    assert data["timing_percentiles_ms"]["drain_monitor_queue"]["p95"] == 6.7
    assert data["timing_percentiles_ms"]["process_automation"]["p50"] == 400.0
    assert data["timing_percentiles_ms"]["process_automation"]["p95"] == 670.0


def test_main_vision_self_test_summary_supports_custom_percentiles(tmp_path, capsys):
    path = tmp_path / "known-history-custom.jsonl"
    rows = [
        {"ok": True, "mode": "json", "report": {"timings_ms": {"http_post": 10}}},
        {"ok": True, "mode": "json", "report": {"timings_ms": {"http_post": 30}}},
        {"ok": True, "mode": "json", "report": {"timings_ms": {"http_post": 50}}},
        {"ok": True, "mode": "json", "report": {"timings_ms": {"http_post": 70}}},
    ]
    path.write_text("\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n", encoding="utf-8")

    rc = main(["vision-self-test-summary", str(path), "--percentiles", "50,90,99"])
    out = capsys.readouterr().out

    assert rc == 0
    data = json.loads(out)
    assert data["ok"] is True
    assert data["percentiles"] == [50, 90, 99]
    assert data["timing_percentiles_ms"]["http_post"] == {
        "p50": 40.0,
        "p90": 64.0,
        "p99": 69.4,
    }


def test_main_vision_self_test_summary_rejects_missing_percentiles_value(tmp_path, capsys):
    path = tmp_path / "h.jsonl"
    path.write_text("{}\n", encoding="utf-8")

    rc = main(["vision-self-test-summary", str(path), "--percentiles"])
    out = capsys.readouterr().out

    assert rc == 1
    data = json.loads(out)
    assert data["ok"] is False
    assert data["error"] == "missing_percentiles_value"


def test_main_vision_self_test_summary_rejects_missing_percentiles_value_equals_syntax(tmp_path, capsys):
    path = tmp_path / "h.jsonl"
    path.write_text("{}\n", encoding="utf-8")

    rc = main(["vision-self-test-summary", str(path), "--percentiles="])
    out = capsys.readouterr().out

    assert rc == 1
    data = json.loads(out)
    assert data["ok"] is False
    assert data["error"] == "missing_percentiles_value"


def test_main_vision_self_test_summary_rejects_invalid_percentiles_value(tmp_path, capsys):
    path = tmp_path / "h.jsonl"
    path.write_text("{}\n", encoding="utf-8")

    rc = main(["vision-self-test-summary", str(path), "--percentiles", "90,abc"])
    out = capsys.readouterr().out

    assert rc == 1
    data = json.loads(out)
    assert data["ok"] is False
    assert data["error"] == "invalid_percentiles_value"


def test_main_vision_self_test_summary_rejects_out_of_range_percentiles(tmp_path, capsys):
    path = tmp_path / "h.jsonl"
    path.write_text("{}\n", encoding="utf-8")

    rc = main(["vision-self-test-summary", str(path), "--percentiles", "50,101"])
    out = capsys.readouterr().out

    assert rc == 1
    data = json.loads(out)
    assert data["ok"] is False
    assert data["error"] == "invalid_percentiles_value"


def test_main_vision_self_test_summary_strict_fails_on_invalid_lines(tmp_path, capsys):
    path = tmp_path / "history.jsonl"
    path.write_text(
        "\n".join(
            [
                json.dumps({"ok": True, "mode": "json"}, sort_keys=True),
                "not-json",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    rc = main(["vision-self-test-summary", str(path), "--strict"])
    out = capsys.readouterr().out

    assert rc == 2
    data = json.loads(out)
    assert data["ok"] is False
    assert data["ema_alpha"] == 0.3
    assert data["error"] == "invalid_history_lines"
    assert data["invalid_lines"] == 1
    assert data["scanned_lines"] == 2
    assert data["invalid_line_rate"] == 0.5
    assert data["invalid_line_rate_ema"] == 0.3
    assert data["invalid_line_rate_previous_window"] is None
    assert data["invalid_line_rate_delta"] is None
    assert data["strict"] is True


def test_main_vision_self_test_summary_strict_succeeds_without_invalid_lines(tmp_path, capsys):
    path = tmp_path / "history-ok.jsonl"
    path.write_text(json.dumps({"ok": True, "mode": "json"}, sort_keys=True) + "\n", encoding="utf-8")

    rc = main(["vision-self-test-summary", str(path), "--strict"])
    out = capsys.readouterr().out

    assert rc == 0
    data = json.loads(out)
    assert data["ok"] is True
    assert data["ema_alpha"] == 0.3
    assert data["invalid_lines"] == 0
    assert data["scanned_lines"] == 1
    assert data["invalid_line_rate"] == 0.0
    assert data["invalid_line_rate_ema"] == 0.0
    assert data["invalid_line_rate_previous_window"] is None
    assert data["invalid_line_rate_delta"] is None


def test_main_vision_self_test_summary_max_invalid_lines_allows_small_corruption(tmp_path, capsys):
    path = tmp_path / "history-threshold-ok.jsonl"
    path.write_text(
        "\n".join(
            [
                json.dumps({"ok": True, "mode": "json"}, sort_keys=True),
                "broken-line",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    rc = main(["vision-self-test-summary", str(path), "--max-invalid-lines", "1"])
    out = capsys.readouterr().out

    assert rc == 0
    data = json.loads(out)
    assert data["ok"] is True
    assert data["ema_alpha"] == 0.3
    assert data["invalid_lines"] == 1
    assert data["scanned_lines"] == 2
    assert data["invalid_line_rate"] == 0.5
    assert data["invalid_line_rate_ema"] == 0.3
    assert data["invalid_line_rate_previous_window"] is None
    assert data["invalid_line_rate_delta"] is None


def test_main_vision_self_test_summary_max_invalid_lines_fails_above_threshold(tmp_path, capsys):
    path = tmp_path / "history-threshold-fail.jsonl"
    path.write_text(
        "\n".join(
            [
                json.dumps({"ok": True, "mode": "json"}, sort_keys=True),
                "broken-line-1",
                "broken-line-2",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    rc = main(["vision-self-test-summary", str(path), "--max-invalid-lines", "1"])
    out = capsys.readouterr().out

    assert rc == 2
    data = json.loads(out)
    assert data["ok"] is False
    assert data["ema_alpha"] == 0.3
    assert data["error"] == "invalid_history_lines"
    assert data["invalid_lines"] == 2
    assert data["scanned_lines"] == 3
    assert data["invalid_line_rate"] == 0.6667
    assert data["invalid_line_rate_ema"] == 0.51
    assert data["invalid_line_rate_previous_window"] is None
    assert data["invalid_line_rate_delta"] is None
    assert data["max_invalid_lines"] == 1
    assert data["strict"] is False


def test_main_vision_self_test_summary_reports_invalid_rate_trend_for_last_window(tmp_path, capsys):
    path = tmp_path / "history-trend.jsonl"
    path.write_text(
        "\n".join(
            [
                json.dumps({"ok": True, "mode": "json"}, sort_keys=True),
                "bad-1",
                json.dumps({"ok": True, "mode": "json"}, sort_keys=True),
                "bad-2",
                "bad-3",
                json.dumps({"ok": True, "mode": "json"}, sort_keys=True),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    rc = main(["vision-self-test-summary", str(path), "--last", "3", "--max-invalid-lines", "2"])
    out = capsys.readouterr().out

    assert rc == 0
    data = json.loads(out)
    assert data["ok"] is True
    assert data["ema_alpha"] == 0.3
    assert data["scanned_lines"] == 3
    assert data["invalid_lines"] == 2
    assert data["invalid_line_rate"] == 0.6667
    assert data["invalid_line_rate_ema"] == 0.7
    assert data["invalid_line_rate_previous_window"] == 0.3333
    assert data["invalid_line_rate_delta"] == 0.3334


def test_main_vision_self_test_summary_supports_custom_ema_alpha(tmp_path, capsys):
    path = tmp_path / "history-ema-alpha.jsonl"
    path.write_text(
        "\n".join(
            [
                json.dumps({"ok": True, "mode": "json"}, sort_keys=True),
                "bad-1",
                "bad-2",
                json.dumps({"ok": True, "mode": "json"}, sort_keys=True),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    rc = main(["vision-self-test-summary", str(path), "--ema-alpha", "0.8"])
    out = capsys.readouterr().out

    assert rc == 0
    data = json.loads(out)
    assert data["ok"] is True
    assert data["ema_alpha"] == 0.8
    assert data["invalid_line_rate_ema"] == 0.192


def test_main_vision_self_test_summary_missing_ema_alpha_value(tmp_path, capsys):
    path = tmp_path / "h.jsonl"
    path.write_text("{}\n", encoding="utf-8")

    rc = main(["vision-self-test-summary", str(path), "--ema-alpha"])
    out = capsys.readouterr().out

    assert rc == 1
    data = json.loads(out)
    assert data["ok"] is False
    assert data["error"] == "missing_ema_alpha_value"


def test_main_vision_self_test_summary_missing_ema_alpha_value_equals_syntax(tmp_path, capsys):
    path = tmp_path / "h.jsonl"
    path.write_text("{}\n", encoding="utf-8")

    rc = main(["vision-self-test-summary", str(path), "--ema-alpha="])
    out = capsys.readouterr().out

    assert rc == 1
    data = json.loads(out)
    assert data["ok"] is False
    assert data["error"] == "missing_ema_alpha_value"


def test_main_vision_self_test_summary_invalid_ema_alpha_value(tmp_path, capsys):
    path = tmp_path / "h.jsonl"
    path.write_text("{}\n", encoding="utf-8")

    rc = main(["vision-self-test-summary", str(path), "--ema-alpha", "abc"])
    out = capsys.readouterr().out

    assert rc == 1
    data = json.loads(out)
    assert data["ok"] is False
    assert data["error"] == "invalid_ema_alpha_value"


def test_main_vision_self_test_summary_rejects_out_of_range_ema_alpha(tmp_path, capsys):
    path = tmp_path / "h.jsonl"
    path.write_text("{}\n", encoding="utf-8")

    rc = main(["vision-self-test-summary", str(path), "--ema-alpha", "0"])
    out = capsys.readouterr().out

    assert rc == 1
    data = json.loads(out)
    assert data["ok"] is False
    assert data["error"] == "invalid_ema_alpha_value"



def test_main_vision_self_test_summary_missing_max_invalid_lines_value(tmp_path, capsys):
    path = tmp_path / "h.jsonl"
    path.write_text("{}\n", encoding="utf-8")

    rc = main(["vision-self-test-summary", str(path), "--max-invalid-lines"])
    out = capsys.readouterr().out

    assert rc == 1
    data = json.loads(out)
    assert data["ok"] is False
    assert data["error"] == "missing_max_invalid_lines_value"


def test_main_vision_self_test_summary_missing_max_invalid_lines_value_equals_syntax(tmp_path, capsys):
    path = tmp_path / "h.jsonl"
    path.write_text("{}\n", encoding="utf-8")

    rc = main(["vision-self-test-summary", str(path), "--max-invalid-lines="])
    out = capsys.readouterr().out

    assert rc == 1
    data = json.loads(out)
    assert data["ok"] is False
    assert data["error"] == "missing_max_invalid_lines_value"


def test_main_vision_self_test_summary_invalid_max_invalid_lines_value(tmp_path, capsys):
    path = tmp_path / "h.jsonl"
    path.write_text("{}\n", encoding="utf-8")

    rc = main(["vision-self-test-summary", str(path), "--max-invalid-lines", "abc"])
    out = capsys.readouterr().out

    assert rc == 1
    data = json.loads(out)
    assert data["ok"] is False
    assert data["error"] == "invalid_max_invalid_lines_value"


def test_main_vision_self_test_summary_rejects_negative_max_invalid_lines(tmp_path, capsys):
    path = tmp_path / "h.jsonl"
    path.write_text("{}\n", encoding="utf-8")

    rc = main(["vision-self-test-summary", str(path), "--max-invalid-lines", "-1"])
    out = capsys.readouterr().out

    assert rc == 1
    data = json.loads(out)
    assert data["ok"] is False
    assert data["error"] == "invalid_max_invalid_lines_value"


def test_main_vision_self_test_summary_delta_gate_passes_when_delta_within_threshold(tmp_path, capsys):
    # Window 1: 1 valid line. Window 2 (last=1): also 1 valid line → delta=0.0
    path = tmp_path / "h.jsonl"
    path.write_text(
        '{"ok": true, "mode": "json"}\n{"ok": true, "mode": "json"}\n',
        encoding="utf-8",
    )

    rc = main(["vision-self-test-summary", str(path), "--last", "1", "--max-invalid-line-rate-delta", "0.5"])
    out = capsys.readouterr().out

    assert rc == 0
    data = json.loads(out)
    assert data["ok"] is True


def test_main_vision_self_test_summary_delta_gate_fails_when_delta_exceeded(tmp_path, capsys):
    # Window 1: all valid. Window 2 (last=1): invalid line only → delta spikes to 1.0
    path = tmp_path / "h.jsonl"
    path.write_text(
        '{"ok": true, "mode": "json"}\nnot-json\n',
        encoding="utf-8",
    )

    rc = main(["vision-self-test-summary", str(path), "--last", "1", "--max-invalid-line-rate-delta", "0.0"])
    out = capsys.readouterr().out

    assert rc == 2
    data = json.loads(out)
    assert data["ok"] is False
    assert data["error"] == "invalid_line_rate_delta_exceeded"
    assert data["invalid_line_rate_delta"] > 0.0
    assert data["max_invalid_line_rate_delta"] == 0.0


def test_main_vision_self_test_summary_delta_gate_no_previous_window_skips_check(tmp_path, capsys):
    # Only one line total, so no previous window → delta check cannot fire
    path = tmp_path / "h.jsonl"
    path.write_text("not-json\n", encoding="utf-8")

    rc = main(["vision-self-test-summary", str(path), "--max-invalid-line-rate-delta", "0.0"])
    out = capsys.readouterr().out

    # Gate should not fire because there's no previous window to compare against
    assert rc == 0
    data = json.loads(out)
    assert data["ok"] is True
    assert data["invalid_line_rate_delta"] is None


def test_main_vision_self_test_summary_missing_max_invalid_line_rate_delta_value(tmp_path, capsys):
    path = tmp_path / "h.jsonl"
    path.write_text("{}\n", encoding="utf-8")

    rc = main(["vision-self-test-summary", str(path), "--max-invalid-line-rate-delta"])
    out = capsys.readouterr().out

    assert rc == 1
    data = json.loads(out)
    assert data["ok"] is False
    assert data["error"] == "missing_max_invalid_line_rate_delta_value"


def test_main_vision_self_test_summary_missing_max_invalid_line_rate_delta_value_equals_syntax(
    tmp_path,
    capsys,
):
    path = tmp_path / "h.jsonl"
    path.write_text("{}\n", encoding="utf-8")

    rc = main(["vision-self-test-summary", str(path), "--max-invalid-line-rate-delta="])
    out = capsys.readouterr().out

    assert rc == 1
    data = json.loads(out)
    assert data["ok"] is False
    assert data["error"] == "missing_max_invalid_line_rate_delta_value"


def test_main_vision_self_test_summary_invalid_max_invalid_line_rate_delta_value(tmp_path, capsys):
    path = tmp_path / "h.jsonl"
    path.write_text("{}\n", encoding="utf-8")

    rc = main(["vision-self-test-summary", str(path), "--max-invalid-line-rate-delta", "abc"])
    out = capsys.readouterr().out

    assert rc == 1
    data = json.loads(out)
    assert data["ok"] is False
    assert data["error"] == "invalid_max_invalid_line_rate_delta_value"


def test_main_vision_self_test_summary_rejects_negative_max_invalid_line_rate_delta(tmp_path, capsys):
    path = tmp_path / "h.jsonl"
    path.write_text("{}\n", encoding="utf-8")

    rc = main(["vision-self-test-summary", str(path), "--max-invalid-line-rate-delta", "-0.1"])
    out = capsys.readouterr().out

    assert rc == 1
    data = json.loads(out)
    assert data["ok"] is False
    assert data["error"] == "invalid_max_invalid_line_rate_delta_value"


def test_main_vision_self_test_summary_delta_gate_with_equals_syntax(tmp_path, capsys):
    path = tmp_path / "h.jsonl"
    path.write_text(
        '{"ok": true, "mode": "json"}\nnot-json\n',
        encoding="utf-8",
    )

    rc = main(["vision-self-test-summary", str(path), "--last", "1", "--max-invalid-line-rate-delta=0.0"])
    out = capsys.readouterr().out

    assert rc == 2
    data = json.loads(out)
    assert data["ok"] is False
    assert data["error"] == "invalid_line_rate_delta_exceeded"


def test_main_vision_self_test_summary_ema_gate_passes_when_ema_within_threshold(tmp_path, capsys):
    # All valid lines → EMA will be 0.0, well within 0.5 threshold
    path = tmp_path / "h.jsonl"
    path.write_text(
        '{"ok": true, "mode": "json"}\n{"ok": true, "mode": "json"}\n',
        encoding="utf-8",
    )

    rc = main(["vision-self-test-summary", str(path), "--max-invalid-line-rate-ema", "0.5"])
    out = capsys.readouterr().out

    assert rc == 0
    data = json.loads(out)
    assert data["ok"] is True


def test_main_vision_self_test_summary_ema_gate_fails_when_ema_exceeded(tmp_path, capsys):
    # All lines invalid → EMA = 1.0 > threshold 0.5
    path = tmp_path / "h.jsonl"
    path.write_text("not-json\nnot-json\nnot-json\n", encoding="utf-8")

    rc = main(["vision-self-test-summary", str(path), "--max-invalid-line-rate-ema", "0.5"])
    out = capsys.readouterr().out

    assert rc == 2
    data = json.loads(out)
    assert data["ok"] is False
    assert data["error"] == "invalid_line_rate_ema_exceeded"
    assert data["invalid_line_rate_ema"] > 0.5
    assert data["max_invalid_line_rate_ema"] == 0.5


def test_main_vision_self_test_summary_ema_gate_with_equals_syntax(tmp_path, capsys):
    path = tmp_path / "h.jsonl"
    path.write_text("not-json\nnot-json\n", encoding="utf-8")

    rc = main(["vision-self-test-summary", str(path), "--max-invalid-line-rate-ema=0.5"])
    out = capsys.readouterr().out

    assert rc == 2
    data = json.loads(out)
    assert data["ok"] is False
    assert data["error"] == "invalid_line_rate_ema_exceeded"


def test_main_vision_self_test_summary_missing_max_invalid_line_rate_ema_value(tmp_path, capsys):
    path = tmp_path / "h.jsonl"
    path.write_text("{}\n", encoding="utf-8")

    rc = main(["vision-self-test-summary", str(path), "--max-invalid-line-rate-ema"])
    out = capsys.readouterr().out

    assert rc == 1
    data = json.loads(out)
    assert data["ok"] is False
    assert data["error"] == "missing_max_invalid_line_rate_ema_value"


def test_main_vision_self_test_summary_missing_max_invalid_line_rate_ema_value_equals_syntax(
    tmp_path,
    capsys,
):
    path = tmp_path / "h.jsonl"
    path.write_text("{}\n", encoding="utf-8")

    rc = main(["vision-self-test-summary", str(path), "--max-invalid-line-rate-ema="])
    out = capsys.readouterr().out

    assert rc == 1
    data = json.loads(out)
    assert data["ok"] is False
    assert data["error"] == "missing_max_invalid_line_rate_ema_value"


def test_main_vision_self_test_summary_invalid_max_invalid_line_rate_ema_value(tmp_path, capsys):
    path = tmp_path / "h.jsonl"
    path.write_text("{}\n", encoding="utf-8")

    rc = main(["vision-self-test-summary", str(path), "--max-invalid-line-rate-ema", "abc"])
    out = capsys.readouterr().out

    assert rc == 1
    data = json.loads(out)
    assert data["ok"] is False
    assert data["error"] == "invalid_max_invalid_line_rate_ema_value"


def test_main_vision_self_test_summary_rejects_out_of_range_max_invalid_line_rate_ema(tmp_path, capsys):
    path = tmp_path / "h.jsonl"
    path.write_text("{}\n", encoding="utf-8")

    for bad_val in ["-0.1", "1.1"]:
        rc = main(["vision-self-test-summary", str(path), "--max-invalid-line-rate-ema", bad_val])
        out = capsys.readouterr().out

        assert rc == 1, f"expected exit 1 for {bad_val}"
        data = json.loads(out)
        assert data["ok"] is False
        assert data["error"] == "invalid_max_invalid_line_rate_ema_value"


# --- env-var defaults ---

def test_main_vision_self_test_summary_env_strict_activates_gate(tmp_path, monkeypatch, capsys):
    path = tmp_path / "h.jsonl"
    path.write_text("not-json\n", encoding="utf-8")
    monkeypatch.setenv("JARVIS_SUMMARY_STRICT", "1")

    rc = main(["vision-self-test-summary", str(path)])
    out = capsys.readouterr().out

    assert rc == 2
    data = json.loads(out)
    assert data["ok"] is False
    assert data["error"] == "invalid_history_lines"


def test_main_vision_self_test_summary_env_strict_cli_flag_also_works(tmp_path, monkeypatch, capsys):
    # CLI --strict should work even without env var
    path = tmp_path / "h.jsonl"
    path.write_text("not-json\n", encoding="utf-8")
    monkeypatch.delenv("JARVIS_SUMMARY_STRICT", raising=False)

    rc = main(["vision-self-test-summary", str(path), "--strict"])
    out = capsys.readouterr().out

    assert rc == 2
    data = json.loads(out)
    assert data["ok"] is False
    assert data["error"] == "invalid_history_lines"


def test_main_vision_self_test_summary_env_max_invalid_lines_triggers_gate(tmp_path, monkeypatch, capsys):
    path = tmp_path / "h.jsonl"
    path.write_text("not-json\nnot-json\n", encoding="utf-8")
    monkeypatch.setenv("JARVIS_MAX_INVALID_LINES", "1")

    rc = main(["vision-self-test-summary", str(path)])
    out = capsys.readouterr().out

    assert rc == 2
    data = json.loads(out)
    assert data["ok"] is False
    assert data["error"] == "invalid_history_lines"


def test_main_vision_self_test_summary_cli_max_invalid_lines_overrides_env(tmp_path, monkeypatch, capsys):
    path = tmp_path / "h.jsonl"
    path.write_text("not-json\nnot-json\n", encoding="utf-8")
    monkeypatch.setenv("JARVIS_MAX_INVALID_LINES", "0")  # env says 0

    rc = main(["vision-self-test-summary", str(path), "--max-invalid-lines", "5"])  # CLI overrides to 5
    out = capsys.readouterr().out

    assert rc == 0
    data = json.loads(out)
    assert data["ok"] is True


def test_main_vision_self_test_summary_env_ema_alpha_changes_sensitivity(tmp_path, monkeypatch, capsys):
    path = tmp_path / "h.jsonl"
    path.write_text('{"ok": true, "mode": "json"}\n', encoding="utf-8")
    monkeypatch.setenv("JARVIS_EMA_ALPHA", "0.9")

    rc = main(["vision-self-test-summary", str(path)])
    out = capsys.readouterr().out

    assert rc == 0
    data = json.loads(out)
    assert data["ema_alpha"] == 0.9


def test_main_vision_self_test_summary_env_ema_alpha_invalid_rejected(tmp_path, monkeypatch, capsys):
    path = tmp_path / "h.jsonl"
    path.write_text("{}\n", encoding="utf-8")
    monkeypatch.setenv("JARVIS_EMA_ALPHA", "bad")

    rc = main(["vision-self-test-summary", str(path)])
    out = capsys.readouterr().out

    assert rc == 1
    data = json.loads(out)
    assert data["ok"] is False
    assert data["error"] == "invalid_ema_alpha_value"
    assert data["source"] == "env"


def test_main_vision_self_test_summary_env_max_invalid_line_rate_delta_triggers_gate(tmp_path, monkeypatch, capsys):
    path = tmp_path / "h.jsonl"
    path.write_text('{"ok": true, "mode": "json"}\nnot-json\n', encoding="utf-8")
    monkeypatch.setenv("JARVIS_MAX_INVALID_LINE_RATE_DELTA", "0.0")

    rc = main(["vision-self-test-summary", str(path), "--last", "1"])
    out = capsys.readouterr().out

    assert rc == 2
    data = json.loads(out)
    assert data["ok"] is False
    assert data["error"] == "invalid_line_rate_delta_exceeded"


def test_main_vision_self_test_summary_env_max_invalid_line_rate_ema_triggers_gate(tmp_path, monkeypatch, capsys):
    path = tmp_path / "h.jsonl"
    path.write_text("not-json\nnot-json\nnot-json\n", encoding="utf-8")
    monkeypatch.setenv("JARVIS_MAX_INVALID_LINE_RATE_EMA", "0.5")

    rc = main(["vision-self-test-summary", str(path)])
    out = capsys.readouterr().out

    assert rc == 2
    data = json.loads(out)
    assert data["ok"] is False
    assert data["error"] == "invalid_line_rate_ema_exceeded"


def test_main_vision_self_test_summary_env_max_invalid_lines_invalid_value(tmp_path, monkeypatch, capsys):
    path = tmp_path / "h.jsonl"
    path.write_text("{}\n", encoding="utf-8")
    monkeypatch.setenv("JARVIS_MAX_INVALID_LINES", "abc")

    rc = main(["vision-self-test-summary", str(path)])
    out = capsys.readouterr().out

    assert rc == 1
    data = json.loads(out)
    assert data["ok"] is False
    assert data["error"] == "invalid_max_invalid_lines_value"
    assert data["source"] == "env"


def test_main_vision_self_test_summary_missing_file(tmp_path, capsys):
    rc = main(["vision-self-test-summary", str(tmp_path / "missing.jsonl")])
    out = capsys.readouterr().out

    assert rc == 1
    data = json.loads(out)
    assert data["ok"] is False
    assert data["error"] == "input_file_not_found"


def test_main_vision_self_test_summary_missing_arg(capsys):
    rc = main(["vision-self-test-summary"])
    out = capsys.readouterr().out

    assert rc == 1
    data = json.loads(out)
    assert data["ok"] is False
    assert data["error"] == "missing_input_file"


def test_main_vision_self_test_summary_mode_filter_and_last(
    tmp_path,
    monkeypatch,
    capsys,
):
    monkeypatch.setenv("JARVIS_EVENT_BUS_DB", str(tmp_path / "events.db"))
    monkeypatch.setenv("JARVIS_APPROVAL_DB", str(tmp_path / "approvals.db"))
    monkeypatch.setenv("JARVIS_AUDIT_DB", str(tmp_path / "audit.db"))

    jsonl_file = tmp_path / "artifacts" / "history-filter.jsonl"
    assert main([
        "vision-self-test",
        "json",
        "--output-file",
        str(jsonl_file),
        "--output-format",
        "jsonl",
    ]) == 0
    capsys.readouterr()
    assert main([
        "vision-self-test",
        "binary",
        "--output-file",
        str(jsonl_file),
        "--output-format",
        "jsonl",
    ]) == 0
    capsys.readouterr()
    assert main([
        "vision-self-test",
        "json",
        "--output-file",
        str(jsonl_file),
        "--output-format",
        "jsonl",
    ]) == 0
    capsys.readouterr()

    rc = main(["vision-self-test-summary", str(jsonl_file), "--mode", "json", "--last", "2"])
    out = capsys.readouterr().out

    assert rc == 0
    data = json.loads(out)
    assert data["ok"] is True
    assert data["mode_filter"] == "json"
    assert data["last"] == 2
    assert data["total_runs"] == 1
    assert data["pass_count"] == 1
    assert data["mode_counts"]["json"] == 1


def test_main_vision_self_test_summary_rejects_invalid_mode_filter(tmp_path, capsys):
    path = tmp_path / "h.jsonl"
    path.write_text("{}\n", encoding="utf-8")

    rc = main(["vision-self-test-summary", str(path), "--mode", "weird"])
    out = capsys.readouterr().out

    assert rc == 1
    data = json.loads(out)
    assert data["ok"] is False
    assert data["error"] == "invalid_mode_filter"


def test_main_vision_self_test_summary_rejects_invalid_last_value(tmp_path, capsys):
    path = tmp_path / "h.jsonl"
    path.write_text("{}\n", encoding="utf-8")

    rc = main(["vision-self-test-summary", str(path), "--last", "0"])
    out = capsys.readouterr().out

    assert rc == 1
    data = json.loads(out)
    assert data["ok"] is False
    assert data["error"] == "invalid_last_value"


def test_main_vision_self_test_summary_rejects_missing_last_value_equals_syntax(tmp_path, capsys):
    path = tmp_path / "h.jsonl"
    path.write_text("{}\n", encoding="utf-8")

    rc = main(["vision-self-test-summary", str(path), "--last="])
    out = capsys.readouterr().out

    assert rc == 1
    data = json.loads(out)
    assert data["ok"] is False
    assert data["error"] == "missing_last_value"


def test_main_smoke_vision_commands_support_mixed_flag_styles(
    tmp_path,
    monkeypatch,
    capsys,
):
    import io
    from PIL import Image

    monkeypatch.setenv("JARVIS_EVENT_BUS_DB", str(tmp_path / "events.db"))
    monkeypatch.setenv("JARVIS_APPROVAL_DB", str(tmp_path / "approvals.db"))
    monkeypatch.setenv("JARVIS_AUDIT_DB", str(tmp_path / "audit.db"))
    monkeypatch.setenv("JARVIS_VISION_SECRET", "")

    img = Image.new("RGB", (24, 24), (220, 40, 40))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    image_path = tmp_path / "smoke-red.jpg"
    image_path.write_bytes(buf.getvalue())

    rc_analyze = main(["vision-analyze", str(image_path), "--max-colors=1", "--no-faces"])
    analyze_out = capsys.readouterr().out
    analyze_payload = json.loads(analyze_out)

    assert rc_analyze == 0
    assert analyze_payload["ok"] is True
    assert analyze_payload["faces"] == []
    assert len(analyze_payload["colors"]) <= 1

    jsonl_file = tmp_path / "artifacts" / "vision-smoke.jsonl"
    rc_self_test = main(
        [
            "vision-self-test",
            "json",
            "--report",
            "--output-file",
            str(jsonl_file),
            "--output-format=jsonl",
        ]
    )
    self_test_out = capsys.readouterr().out
    self_test_payload = json.loads(self_test_out)

    assert rc_self_test == 0
    assert self_test_payload["ok"] is True
    assert self_test_payload["output_format"] == "jsonl"
    assert self_test_payload["output_file"] == str(jsonl_file)

    rc_summary = main(
        [
            "vision-self-test-summary",
            str(jsonl_file),
            "--mode",
            "json",
            "--last=1",
            "--percentiles",
            "50,95",
        ]
    )
    summary_out = capsys.readouterr().out
    summary_payload = json.loads(summary_out)

    assert rc_summary == 0
    assert summary_payload["ok"] is True
    assert summary_payload["mode_filter"] == "json"
    assert summary_payload["last"] == 1
    assert summary_payload["percentiles"] == [50, 95]
    assert summary_payload["total_runs"] == 1


def test_main_events_process_creates_approval_from_event(tmp_path, monkeypatch, capsys):
    bus_db = tmp_path / "events.db"
    approvals_db = tmp_path / "approvals.db"
    audit_db = tmp_path / "audit.db"
    bus = EventBus(bus_db)
    bus.emit(
        Event(
            kind="webhook_github",
            source="webhook_secure",
            payload={
                "event_type": "github.push",
                "path": "/github/push",
                "payload": {"repo": "jarvis", "action": "push"},
            },
        )
    )

    monkeypatch.setenv("JARVIS_EVENT_BUS_DB", str(bus_db))
    monkeypatch.setenv("JARVIS_APPROVAL_DB", str(approvals_db))
    monkeypatch.setenv("JARVIS_AUDIT_DB", str(audit_db))
    monkeypatch.setenv("JARVIS_EVENT_ALERT_CHANNEL", "slack")
    monkeypatch.setenv("JARVIS_EVENT_ALERT_RECIPIENT", "#ops")

    rc = main(["events-process", "10"])
    out = capsys.readouterr().out.strip()

    assert rc == 0
    data = json.loads(out)
    assert data["processed"] == 1
    assert data["approvals_created"] == 1
    assert data["duplicates"] == 0
    assert data["throttled"] == 0
    assert data["failures"] == 0


def test_main_events_process_returns_zero_when_no_events(tmp_path, monkeypatch, capsys):
    bus_db = tmp_path / "events.db"
    approvals_db = tmp_path / "approvals.db"
    audit_db = tmp_path / "audit.db"

    monkeypatch.setenv("JARVIS_EVENT_BUS_DB", str(bus_db))
    monkeypatch.setenv("JARVIS_APPROVAL_DB", str(approvals_db))
    monkeypatch.setenv("JARVIS_AUDIT_DB", str(audit_db))

    rc = main(["events-process"])
    out = capsys.readouterr().out.strip()

    assert rc == 0
    data = json.loads(out)
    assert data["processed"] == 0
    assert data["approvals_created"] == 0
    assert data["duplicates"] == 0
    assert data["throttled"] == 0


def test_main_events_list_invalid_limit_value_errors(capsys):
    rc = main(["events-list", "abc"])
    out = capsys.readouterr().out.strip()

    assert rc == 1
    payload = json.loads(out)
    assert payload["ok"] is False
    assert payload["error"] == "invalid_limit_value"


def test_main_events_list_zero_limit_value_errors(capsys):
    rc = main(["events-list", "0"])
    out = capsys.readouterr().out.strip()

    assert rc == 1
    payload = json.loads(out)
    assert payload["ok"] is False
    assert payload["error"] == "invalid_limit_value"


def test_main_events_list_negative_limit_value_errors(capsys):
    rc = main(["events-list", "-5"])
    out = capsys.readouterr().out.strip()

    assert rc == 1
    payload = json.loads(out)
    assert payload["ok"] is False
    assert payload["error"] == "invalid_limit_value"


def test_main_events_process_invalid_limit_value_errors(capsys):
    rc = main(["events-process", "abc"])
    out = capsys.readouterr().out.strip()

    assert rc == 1
    payload = json.loads(out)
    assert payload["ok"] is False
    assert payload["error"] == "invalid_limit_value"


def test_main_events_process_zero_limit_value_errors(capsys):
    rc = main(["events-process", "0"])
    out = capsys.readouterr().out.strip()

    assert rc == 1
    payload = json.loads(out)
    assert payload["ok"] is False
    assert payload["error"] == "invalid_limit_value"


def test_main_events_process_negative_limit_value_errors(capsys):
    rc = main(["events-process", "-5"])
    out = capsys.readouterr().out.strip()

    assert rc == 1
    payload = json.loads(out)
    assert payload["ok"] is False
    assert payload["error"] == "invalid_limit_value"


def test_main_events_actions_lists_history(tmp_path, monkeypatch, capsys):
    bus_db = tmp_path / "events.db"
    approvals_db = tmp_path / "approvals.db"
    audit_db = tmp_path / "audit.db"
    bus = EventBus(bus_db)
    bus.emit(
        Event(
            kind="webhook_github",
            source="webhook_secure",
            payload={
                "event_type": "github.push",
                "path": "/github/push",
                "payload": {"repo": "jarvis", "action": "push"},
            },
        )
    )

    monkeypatch.setenv("JARVIS_EVENT_BUS_DB", str(bus_db))
    monkeypatch.setenv("JARVIS_APPROVAL_DB", str(approvals_db))
    monkeypatch.setenv("JARVIS_AUDIT_DB", str(audit_db))
    monkeypatch.setenv("JARVIS_EVENT_ALERT_CHANNEL", "slack")
    monkeypatch.setenv("JARVIS_EVENT_ALERT_RECIPIENT", "#ops")

    assert main(["events-process", "10"]) == 0
    rc = main(["events-actions", "10"])
    lines = [line for line in capsys.readouterr().out.splitlines() if line.strip()]

    assert rc == 0
    data = json.loads(lines[-1])
    assert data["event_kind"] == "webhook_github"
    assert data["action"] == "approval_created"
    assert data["correlation_id"]


def test_main_events_actions_invalid_limit_value_errors(capsys):
    rc = main(["events-actions", "abc"])
    out = capsys.readouterr().out.strip()

    assert rc == 1
    payload = json.loads(out)
    assert payload["ok"] is False
    assert payload["error"] == "invalid_limit_value"


def test_main_events_actions_zero_limit_value_errors(capsys):
    rc = main(["events-actions", "0"])
    out = capsys.readouterr().out.strip()

    assert rc == 1
    payload = json.loads(out)
    assert payload["ok"] is False
    assert payload["error"] == "invalid_limit_value"


def test_main_events_actions_negative_limit_value_errors(capsys):
    rc = main(["events-actions", "-5"])
    out = capsys.readouterr().out.strip()

    assert rc == 1
    payload = json.loads(out)
    assert payload["ok"] is False
    assert payload["error"] == "invalid_limit_value"


def test_main_cli_parser_latency_budget_for_common_commands(capsys):
    cases = [
        ("audit-correlation", ["audit-correlation", "corr", "--limit", "oops"]),
        ("events-list", ["events-list", "oops"]),
        ("events-actions", ["events-actions", "oops"]),
    ]
    iterations_per_case = 25
    total_start = time.perf_counter()
    per_case_avg_ms = {}

    # Use parser-failure paths to benchmark CLI argument handling without I/O-heavy work.
    for case_name, argv in cases:
        case_start = time.perf_counter()
        for _ in range(iterations_per_case):
            rc = main(argv)
            out = capsys.readouterr().out.strip()
            payload = json.loads(out)
            assert rc == 1
            assert payload["ok"] is False
            assert payload["error"] == "invalid_limit_value"
        case_elapsed_ms = (time.perf_counter() - case_start) * 1000
        per_case_avg_ms[case_name] = case_elapsed_ms / iterations_per_case

    total_elapsed_ms = (time.perf_counter() - total_start) * 1000

    # Keep the budget intentionally loose to avoid flakiness while still catching large regressions.
    assert total_elapsed_ms < 5000
    assert max(per_case_avg_ms.values()) < 250


def test_main_events_actions_can_filter_by_kind(tmp_path, monkeypatch, capsys):
    bus_db = tmp_path / "events.db"
    approvals_db = tmp_path / "approvals.db"
    audit_db = tmp_path / "audit.db"
    bus = EventBus(bus_db)
    bus.emit(
        Event(
            kind="webhook_github",
            source="webhook_secure",
            payload={
                "event_type": "github.push",
                "path": "/github/push",
                "payload": {"repo": "jarvis", "action": "push"},
            },
        )
    )
    bus.emit(Event(kind="rss_article", source="rss_demo", payload={"title": "x"}))

    monkeypatch.setenv("JARVIS_EVENT_BUS_DB", str(bus_db))
    monkeypatch.setenv("JARVIS_APPROVAL_DB", str(approvals_db))
    monkeypatch.setenv("JARVIS_AUDIT_DB", str(audit_db))

    assert main(["events-process", "10"]) == 0
    capsys.readouterr()
    rc = main(["events-actions", "20", "rss_article"])
    lines = [line for line in capsys.readouterr().out.splitlines() if line.strip()]

    assert rc == 0
    parsed = [json.loads(line) for line in lines]
    assert parsed
    assert all(item["event_kind"] == "rss_article" for item in parsed)
    assert all("correlation_id" in item for item in parsed)


def test_main_events_actions_can_filter_by_correlation_id(tmp_path, monkeypatch, capsys):
    bus_db = tmp_path / "events.db"
    approvals_db = tmp_path / "approvals.db"
    audit_db = tmp_path / "audit.db"
    bus = EventBus(bus_db)
    bus.emit(
        Event(
            kind="rss_article",
            source="rss_demo",
            payload={"correlation_id": "corr-a", "title": "a"},
        )
    )
    bus.emit(
        Event(
            kind="rss_article",
            source="rss_demo",
            payload={"correlation_id": "corr-b", "title": "b"},
        )
    )

    monkeypatch.setenv("JARVIS_EVENT_BUS_DB", str(bus_db))
    monkeypatch.setenv("JARVIS_APPROVAL_DB", str(approvals_db))
    monkeypatch.setenv("JARVIS_AUDIT_DB", str(audit_db))

    assert main(["events-process", "10"]) == 0
    capsys.readouterr()

    rc = main(["events-actions", "20", "--correlation-id", "corr-a"])
    lines = [line for line in capsys.readouterr().out.splitlines() if line.strip()]

    assert rc == 0
    parsed = [json.loads(line) for line in lines]
    assert parsed
    assert all(item["correlation_id"] == "corr-a" for item in parsed)


def test_main_events_actions_can_filter_by_kind_and_correlation_id(
    tmp_path,
    monkeypatch,
    capsys,
):
    bus_db = tmp_path / "events.db"
    approvals_db = tmp_path / "approvals.db"
    audit_db = tmp_path / "audit.db"
    bus = EventBus(bus_db)
    bus.emit(
        Event(
            kind="rss_article",
            source="rss_demo",
            payload={"correlation_id": "corr-z", "title": "a"},
        )
    )
    bus.emit(
        Event(
            kind="webhook_github",
            source="webhook_secure",
            payload={
                "correlation_id": "corr-z",
                "event_type": "github.push",
                "path": "/github/push",
                "payload": {"repo": "jarvis", "action": "push"},
            },
        )
    )

    monkeypatch.setenv("JARVIS_EVENT_BUS_DB", str(bus_db))
    monkeypatch.setenv("JARVIS_APPROVAL_DB", str(approvals_db))
    monkeypatch.setenv("JARVIS_AUDIT_DB", str(audit_db))

    assert main(["events-process", "10"]) == 0
    capsys.readouterr()

    rc = main(["events-actions", "20", "rss_article", "--correlation-id", "corr-z"])
    lines = [line for line in capsys.readouterr().out.splitlines() if line.strip()]

    assert rc == 0
    parsed = [json.loads(line) for line in lines]
    assert parsed
    assert all(item["event_kind"] == "rss_article" for item in parsed)
    assert all(item["correlation_id"] == "corr-z" for item in parsed)


def test_main_smoke_audit_and_events_actions_support_mixed_flag_styles(
    tmp_path,
    monkeypatch,
    capsys,
):
    audit_db = tmp_path / "audit.db"
    bus_db = tmp_path / "events.db"
    approvals_db = tmp_path / "approvals.db"

    corr = "corr-smoke-mixed"

    # Seed audit events so audit-correlation can be queried with mixed flag styles.
    log = AuditLog(audit_db)
    log.append("user_input", {"text": "hello", "correlation_id": corr})
    log.append("tool_call", {"name": "web_fetch", "correlation_id": corr})

    # Seed event bus and process once so events-actions has automation rows.
    bus = EventBus(bus_db)
    bus.emit(
        Event(
            kind="rss_article",
            source="rss_demo",
            payload={"correlation_id": corr, "title": "x"},
        )
    )

    monkeypatch.setenv("JARVIS_AUDIT_DB", str(audit_db))
    monkeypatch.setenv("JARVIS_EVENT_BUS_DB", str(bus_db))
    monkeypatch.setenv("JARVIS_APPROVAL_DB", str(approvals_db))

    assert main(["events-process", "10"]) == 0
    capsys.readouterr()

    rc_audit = main(["audit-correlation", corr, "--limit=5", "--kind", "tool_call"])
    audit_out = capsys.readouterr().out
    audit_payload = json.loads(audit_out)

    assert rc_audit == 0
    assert audit_payload["ok"] is True
    assert audit_payload["correlation_id"] == corr
    assert audit_payload["kind"] == "tool_call"
    assert audit_payload["count"] == 1
    assert audit_payload["events"][0]["kind"] == "tool_call"

    rc_actions = main(["events-actions", "20", "--kind=rss_article", "--correlation-id", corr])
    lines = [line for line in capsys.readouterr().out.splitlines() if line.strip()]

    assert rc_actions == 0
    parsed = [json.loads(line) for line in lines]
    assert parsed
    assert all(item["event_kind"] == "rss_article" for item in parsed)
    assert all(item["correlation_id"] == corr for item in parsed)


def test_main_events_actions_supports_equals_syntax_for_correlation_id(
    tmp_path,
    monkeypatch,
    capsys,
):
    bus_db = tmp_path / "events.db"
    approvals_db = tmp_path / "approvals.db"
    audit_db = tmp_path / "audit.db"
    bus = EventBus(bus_db)
    bus.emit(
        Event(
            kind="rss_article",
            source="rss_demo",
            payload={"correlation_id": "corr-eq", "title": "a"},
        )
    )

    monkeypatch.setenv("JARVIS_EVENT_BUS_DB", str(bus_db))
    monkeypatch.setenv("JARVIS_APPROVAL_DB", str(approvals_db))
    monkeypatch.setenv("JARVIS_AUDIT_DB", str(audit_db))

    assert main(["events-process", "10"]) == 0
    capsys.readouterr()

    rc = main(["events-actions", "20", "--correlation-id=corr-eq"])
    lines = [line for line in capsys.readouterr().out.splitlines() if line.strip()]

    assert rc == 0
    parsed = [json.loads(line) for line in lines]
    assert parsed
    assert all(item["correlation_id"] == "corr-eq" for item in parsed)


def test_main_events_actions_missing_correlation_id_value_errors(capsys):
    rc = main(["events-actions", "20", "--correlation-id"])
    out = capsys.readouterr().out.strip()

    assert rc == 1
    payload = json.loads(out)
    assert payload["ok"] is False
    assert payload["error"] == "missing_correlation_id_value"


def test_main_events_actions_unknown_flag_errors(capsys):
    rc = main(["events-actions", "20", "--bad-flag"])
    out = capsys.readouterr().out.strip()

    assert rc == 1
    payload = json.loads(out)
    assert payload["ok"] is False
    assert payload["error"] == "unknown_argument"
    assert payload["argument"] == "--bad-flag"


def test_main_events_actions_extra_positional_argument_errors(capsys):
    rc = main(["events-actions", "20", "rss_article", "extra-token"])
    out = capsys.readouterr().out.strip()

    assert rc == 1
    payload = json.loads(out)
    assert payload["ok"] is False
    assert payload["error"] == "unknown_argument"
    assert payload["argument"] == "extra-token"


def test_main_events_actions_can_filter_by_kind_flag(tmp_path, monkeypatch, capsys):
    bus_db = tmp_path / "events.db"
    approvals_db = tmp_path / "approvals.db"
    audit_db = tmp_path / "audit.db"
    bus = EventBus(bus_db)
    bus.emit(Event(kind="rss_article", source="rss_demo", payload={"title": "x"}))
    bus.emit(
        Event(
            kind="webhook_github",
            source="webhook_secure",
            payload={
                "event_type": "github.push",
                "path": "/github/push",
                "payload": {"repo": "jarvis", "action": "push"},
            },
        )
    )

    monkeypatch.setenv("JARVIS_EVENT_BUS_DB", str(bus_db))
    monkeypatch.setenv("JARVIS_APPROVAL_DB", str(approvals_db))
    monkeypatch.setenv("JARVIS_AUDIT_DB", str(audit_db))

    assert main(["events-process", "10"]) == 0
    capsys.readouterr()

    rc = main(["events-actions", "20", "--kind", "rss_article"])
    lines = [line for line in capsys.readouterr().out.splitlines() if line.strip()]

    assert rc == 0
    parsed = [json.loads(line) for line in lines]
    assert parsed
    assert all(item["event_kind"] == "rss_article" for item in parsed)


def test_main_events_actions_can_filter_by_kind_equals_syntax(tmp_path, monkeypatch, capsys):
    bus_db = tmp_path / "events.db"
    approvals_db = tmp_path / "approvals.db"
    audit_db = tmp_path / "audit.db"
    bus = EventBus(bus_db)
    bus.emit(Event(kind="rss_article", source="rss_demo", payload={"title": "x"}))

    monkeypatch.setenv("JARVIS_EVENT_BUS_DB", str(bus_db))
    monkeypatch.setenv("JARVIS_APPROVAL_DB", str(approvals_db))
    monkeypatch.setenv("JARVIS_AUDIT_DB", str(audit_db))

    assert main(["events-process", "10"]) == 0
    capsys.readouterr()

    rc = main(["events-actions", "20", "--kind=rss_article"])
    lines = [line for line in capsys.readouterr().out.splitlines() if line.strip()]

    assert rc == 0
    parsed = [json.loads(line) for line in lines]
    assert parsed
    assert all(item["event_kind"] == "rss_article" for item in parsed)


def test_main_events_actions_missing_kind_value_errors(capsys):
    rc = main(["events-actions", "20", "--kind"])
    out = capsys.readouterr().out.strip()

    assert rc == 1
    payload = json.loads(out)
    assert payload["ok"] is False
    assert payload["error"] == "missing_kind_value"


def test_main_events_actions_empty_kind_equals_value_errors(capsys):
    rc = main(["events-actions", "20", "--kind="])
    out = capsys.readouterr().out.strip()

    assert rc == 1
    payload = json.loads(out)
    assert payload["ok"] is False
    assert payload["error"] == "missing_kind_value"


def test_main_events_actions_conflicting_positional_and_flag_kind_errors(capsys):
    rc = main(["events-actions", "20", "rss_article", "--kind", "webhook_github"])
    out = capsys.readouterr().out.strip()

    assert rc == 1
    payload = json.loads(out)
    assert payload["ok"] is False
    assert payload["error"] == "conflicting_kind_filters"


def test_main_events_actions_conflicting_repeated_kind_flags_error(capsys):
    rc = main(["events-actions", "20", "--kind", "rss_article", "--kind", "webhook_github"])
    out = capsys.readouterr().out.strip()

    assert rc == 1
    payload = json.loads(out)
    assert payload["ok"] is False
    assert payload["error"] == "conflicting_kind_filters"


def test_main_events_actions_repeated_same_kind_flags_allowed(capsys):
    rc = main(["events-actions", "20", "--kind", "rss_article", "--kind=rss_article"])
    out = capsys.readouterr().out.strip()

    assert rc == 0
    assert out == "No automation actions found."


def test_main_events_actions_empty_correlation_id_equals_value_errors(capsys):
    rc = main(["events-actions", "20", "--correlation-id="])
    out = capsys.readouterr().out.strip()

    assert rc == 1
    payload = json.loads(out)
    assert payload["ok"] is False
    assert payload["error"] == "missing_correlation_id_value"


def test_main_events_actions_conflicting_repeated_correlation_id_flags_error(capsys):
    rc = main(["events-actions", "20", "--correlation-id", "corr-a", "--correlation-id", "corr-b"])
    out = capsys.readouterr().out.strip()

    assert rc == 1
    payload = json.loads(out)
    assert payload["ok"] is False
    assert payload["error"] == "conflicting_correlation_id_filters"


def test_main_events_actions_repeated_same_correlation_id_flags_allowed(capsys):
    rc = main(["events-actions", "20", "--correlation-id", "corr-a", "--correlation-id=corr-a"])
    out = capsys.readouterr().out.strip()

    assert rc == 0
    assert out == "No automation actions found."


def test_main_events_prune_actions_deletes_old_rows(tmp_path, monkeypatch, capsys):
    bus_db = tmp_path / "events.db"
    approvals_db = tmp_path / "approvals.db"
    audit_db = tmp_path / "audit.db"
    bus = EventBus(bus_db)
    bus.emit(
        Event(
            kind="webhook_github",
            source="webhook_secure",
            payload={
                "event_type": "github.push",
                "path": "/github/push",
                "payload": {"repo": "jarvis", "action": "push"},
            },
        )
    )

    monkeypatch.setenv("JARVIS_EVENT_BUS_DB", str(bus_db))
    monkeypatch.setenv("JARVIS_APPROVAL_DB", str(approvals_db))
    monkeypatch.setenv("JARVIS_AUDIT_DB", str(audit_db))

    assert main(["events-process", "10"]) == 0

    import sqlite3
    with sqlite3.connect(bus_db) as con:
        con.execute("UPDATE automation_actions SET ts = ?", (0.0,))

    capsys.readouterr()
    rc = main(["events-prune-actions", "1"])
    out = capsys.readouterr().out.strip()

    assert rc == 0
    data = json.loads(out)
    assert data["older_than_days"] == 1
    assert data["deleted"] >= 1


def test_main_events_prune_actions_uses_default_retention(tmp_path, monkeypatch, capsys):
    bus_db = tmp_path / "events.db"
    approvals_db = tmp_path / "approvals.db"
    audit_db = tmp_path / "audit.db"
    monkeypatch.setenv("JARVIS_EVENT_BUS_DB", str(bus_db))
    monkeypatch.setenv("JARVIS_APPROVAL_DB", str(approvals_db))
    monkeypatch.setenv("JARVIS_AUDIT_DB", str(audit_db))
    monkeypatch.setenv("JARVIS_EVENT_ACTIONS_RETENTION_DAYS", "45")

    rc = main(["events-prune-actions"])
    out = capsys.readouterr().out.strip()

    assert rc == 0
    data = json.loads(out)
    assert data["older_than_days"] == 45

