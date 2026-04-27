import time
import sqlite3
from unittest.mock import patch

from jarvis.approval import ApprovalEnvelope
from jarvis.approval_service import ApprovalService
from jarvis.audit import AuditLog
from jarvis.config import Config


def _config(tmp_path):
    return Config(
        anthropic_api_key="test-key",
        model="claude-sonnet-4-6",
        notes_dir=tmp_path / "notes",
        audit_db=tmp_path / "audit.db",
        user_name="Nick",
        approval_db=tmp_path / "approvals.db",
        message_outbox=tmp_path / "outbox.jsonl",
    )


def test_approval_service_emits_request_approve_dispatch_events(tmp_path):
    cfg = _config(tmp_path)
    service = ApprovalService(cfg)

    approval_id = service.request(
        "message_send",
        {
            "channel": "email",
            "recipient": "user@example.com",
            "subject": "Hi",
            "body": "hello",
        },
    )
    assert service.approve(approval_id, reason="ok")

    summary = service.dispatch(limit=100)

    assert summary.failures == 0
    audit = AuditLog(cfg.audit_db)
    recent = audit.recent(limit=20)
    kinds = [r["kind"] for r in recent]
    assert "approval_requested" in kinds
    assert "approval_approved" in kinds
    assert "approval_dispatched" in kinds

    requested = audit.recent(limit=20, kind="approval_requested")[0]
    approved = audit.recent(limit=20, kind="approval_approved")[0]
    dispatched = audit.recent(limit=20, kind="approval_dispatched")[0]

    cid = requested["payload"]["correlation_id"]
    assert cid
    assert approved["payload"]["correlation_id"] == cid
    assert dispatched["payload"]["correlation_id"] == cid


def test_approval_service_integration_request_approve_dispatch_flow(tmp_path):
    cfg = _config(tmp_path)
    service = ApprovalService(cfg)

    approval_id = service.request(
        "message_send",
        {
            "channel": "email",
            "recipient": "user@example.com",
            "subject": "Integration",
            "body": "full flow",
        },
    )
    row = service.store.get(approval_id)
    assert row is not None
    correlation_id = row["correlation_id"]

    assert service.approve(approval_id, reason="ship it")
    summary = service.dispatch(limit=10)

    assert summary.failures == 0
    assert len(summary.items) == 1

    processed = service.store.get(approval_id)
    assert processed is not None
    assert processed["status"] == "processed"
    assert processed["dispatch_result"]["status"] == "dry_run_sent"

    audit = AuditLog(cfg.audit_db)
    events = audit.by_correlation_id(correlation_id, limit=10)

    assert [event["kind"] for event in events] == [
        "approval_dispatched",
        "approval_approved",
        "approval_requested",
    ]


def test_approval_service_emits_expired_event(tmp_path):
    cfg = _config(tmp_path)
    cfg.approvals_ttl_seconds = 300
    service = ApprovalService(cfg)

    stale_id = service.store.request(
        "message_send",
        {"channel": "email", "recipient": "u", "body": "x"},
        created_ts=time.time() - 3600,
    )

    _ = service.list_pending(limit=10)

    row = service.store.get(stale_id)
    assert row is not None
    assert row["status"] == "rejected"

    audit = AuditLog(cfg.audit_db)
    expired = audit.recent(limit=20, kind="approval_expired")
    assert len(expired) >= 1
    assert expired[0]["payload"]["approval_id"] == stale_id
    assert expired[0]["payload"]["correlation_id"]


def test_approval_service_integration_ttl_expiry_prevents_dispatch(tmp_path):
    cfg = _config(tmp_path)
    cfg.approvals_ttl_seconds = 300
    service = ApprovalService(cfg)

    stale_id = service.store.request(
        "message_send",
        {"channel": "email", "recipient": "u", "body": "stale"},
        created_ts=time.time() - 3600,
    )

    expired_pending = service.list_pending(limit=10)
    summary = service.dispatch(limit=10)

    assert expired_pending == []
    assert summary.items == []
    assert summary.skipped_reason == "none_approved"

    stale = service.store.get(stale_id)
    assert stale is not None
    assert stale["status"] == "rejected"
    assert "expired" in stale["decision_reason"]


def test_approval_service_edit_updates_pending_and_emits_event(tmp_path):
    cfg = _config(tmp_path)
    service = ApprovalService(cfg)

    approval_id = service.request(
        "message_send",
        {
            "channel": "email",
            "recipient": "user@example.com",
            "subject": "Hi",
            "body": "hello",
        },
    )

    ok = service.edit(
        approval_id,
        payload={
            "channel": "email",
            "recipient": "user@example.com",
            "subject": "Edited",
            "body": "updated",
        },
        envelope=ApprovalEnvelope(
            action="send_updated_email",
            reason="user correction",
            budget_impact=0.0,
            ttl_seconds=300,
            risk_tier="high",
        ),
    )
    assert ok is True

    row = service.store.get(approval_id)
    assert row is not None
    assert row["status"] == "pending"
    assert row["payload"]["subject"] == "Edited"
    assert row["action"] == "send_updated_email"
    assert row["reason"] == "user correction"
    assert row["ttl_seconds"] == 300
    assert row["risk_tier"] == "high"

    audit = AuditLog(cfg.audit_db)
    edited = audit.recent(limit=20, kind="approval_edited")
    assert len(edited) >= 1
    assert edited[0]["payload"]["approval_id"] == approval_id


def test_approval_service_tier_cooldown_skips_high_risk_recent_approval(tmp_path):
    cfg = _config(tmp_path)
    service = ApprovalService(cfg)

    approval_id = service.request(
        "message_send",
        {
            "channel": "email",
            "recipient": "user@example.com",
            "subject": "High",
            "body": "risk",
        },
        envelope=ApprovalEnvelope(risk_tier="high"),
    )
    assert service.approve(approval_id)

    summary = service.dispatch(limit=10)
    assert summary.failures == 0
    assert summary.items == []
    assert summary.skipped_reason in {"tier_cooldown", "kind_or_tier_cooldown"}
    assert summary.skipped_by_tier_cooldown >= 1

    row = service.store.get(approval_id)
    assert row is not None
    assert row["status"] == "approved"


def test_approval_service_tier_cooldown_allows_after_wait_window(tmp_path):
    cfg = _config(tmp_path)
    service = ApprovalService(cfg)

    approval_id = service.request(
        "message_send",
        {
            "channel": "email",
            "recipient": "user@example.com",
            "subject": "High",
            "body": "risk",
        },
        envelope=ApprovalEnvelope(risk_tier="high"),
    )
    assert service.approve(approval_id)

    # Force decision_ts to older than the 5s cooldown so dispatch can proceed.
    with sqlite3.connect(cfg.approval_db) as con:
        con.execute(
            "UPDATE approvals SET decision_ts = ? WHERE id = ?",
            (time.time() - 10, approval_id),
        )

    summary = service.dispatch(limit=10)
    assert summary.failures == 0
    assert len(summary.items) == 1

    row = service.store.get(approval_id)
    assert row is not None
    assert row["status"] == "processed"


def test_approval_service_dispatch_treats_twilio_queued_as_success(tmp_path):
    cfg = _config(tmp_path)
    cfg.call_phone_mode = "live"
    cfg.telephony_provider = "twilio"
    cfg.telephony_caller_id = "+14155550000"
    service = ApprovalService(cfg)

    approval_id = service.request(
        "call_phone",
        {
            "phone_number": "+14155552671",
            "subject": "Reminder",
            "message": "This is a reminder call",
        },
    )
    assert service.approve(approval_id)

    with patch("jarvis.approval_service.dispatch_call_phone") as mock_dispatch:
        mock_dispatch.return_value = {
            "status": "twilio_queued",
            "provider": "twilio",
            "call_id": "CA555",
        }
        summary = service.dispatch(limit=10)

    assert summary.failures == 0
    assert len(summary.items) == 1
    row = service.store.get(approval_id)
    assert row is not None
    assert row["status"] == "processed"


def test_approval_service_call_phone_persists_recording_and_transcript_in_audit(tmp_path):
    cfg = _config(tmp_path)
    service = ApprovalService(cfg)

    approval_id = service.request(
        "call_phone",
        {
            "phone_number": "+14155552671",
            "subject": "Reminder",
            "message": "This is a reminder call",
        },
    )
    assert service.approve(approval_id)

    summary = service.dispatch(limit=10)
    assert summary.failures == 0
    assert len(summary.items) == 1

    audit = AuditLog(cfg.audit_db)
    dispatched = audit.recent(limit=20, kind="approval_dispatched")
    payload = dispatched[0]["payload"]
    result = payload["result"]

    assert payload["approval_id"] == approval_id
    assert result["status"] == "dry_run_logged"
    assert result["recording_url"].startswith("dry-run://call-recordings/")
    assert result["transcript"].startswith("[dry_run transcript] ")


def test_approval_service_call_phone_human_handoff_dispatches_successfully(tmp_path):
    cfg = _config(tmp_path)
    service = ApprovalService(cfg)

    approval_id = service.request(
        "call_phone",
        {
            "phone_number": "+14155552671",
            "subject": "Reminder",
            "message": "This is a reminder call",
            "human_requested": True,
            "handoff_reason": "recipient asked for a person",
        },
    )
    assert service.approve(approval_id)

    summary = service.dispatch(limit=10)
    assert summary.failures == 0
    assert len(summary.items) == 1

    row = service.store.get(approval_id)
    assert row is not None
    assert row["status"] == "processed"

    audit = AuditLog(cfg.audit_db)
    dispatched = audit.recent(limit=20, kind="approval_dispatched")
    payload = dispatched[0]["payload"]
    result = payload["result"]

    assert payload["approval_id"] == approval_id
    assert result["status"] == "human_handoff_requested"
    assert result["handoff_required"] is True
    assert result["handoff_reason"] == "recipient asked for a person"


def test_approval_service_dispatch_treats_paper_trade_as_success(tmp_path):
    cfg = _config(tmp_path)
    cfg.trades_mode = "paper"
    cfg.trading_paper_broker = "alpaca"
    service = ApprovalService(cfg)

    approval_id = service.request(
        "trade",
        {
            "instrument": "AAPL",
            "side": "buy",
            "size": 10,
            "reason": "Paper entry",
        },
    )
    assert service.approve(approval_id)

    with patch("jarvis.approval_service.dispatch_trade") as mock_dispatch:
        mock_dispatch.return_value = {
            "status": "paper_submitted",
            "order_id": "ord_123",
            "paper_broker": "alpaca",
            "broker_status": "accepted",
        }
        summary = service.dispatch(limit=10)

    assert summary.failures == 0
    assert len(summary.items) == 1
    row = service.store.get(approval_id)
    assert row is not None
    assert row["status"] == "processed"


def test_approval_service_dispatch_treats_live_trade_as_success(tmp_path):
    cfg = _config(tmp_path)
    cfg.trades_mode = "live"
    cfg.trading_paper_broker = "alpaca"
    cfg.trading_live_cooldown_seconds = 0
    service = ApprovalService(cfg)

    approval_id = service.request(
        "trade",
        {
            "instrument": "AAPL",
            "side": "buy",
            "size": 10,
            "reason": "Live entry",
            "live_confirm": True,
        },
    )
    assert service.approve(approval_id)

    with patch("jarvis.approval_service.dispatch_trade") as mock_dispatch:
        mock_dispatch.return_value = {
            "status": "live_submitted",
            "order_id": "ord_live_123",
            "paper_broker": "alpaca",
            "broker_status": "accepted",
        }
        summary = service.dispatch(limit=10)

    assert summary.failures == 0
    assert len(summary.items) == 1
    row = service.store.get(approval_id)
    assert row is not None
    assert row["status"] == "processed"


def test_approval_service_dispatch_treats_install_app_success_as_processed(tmp_path):
    cfg = _config(tmp_path)
    service = ApprovalService(cfg)

    approval_id = service.request(
        "install_app",
        {
            "app": "spotify",
            "method": "auto",
            "open_after_download": True,
        },
    )
    assert service.approve(approval_id)

    with patch("jarvis.approval_service.dispatch_install_app") as mock_dispatch:
        mock_dispatch.return_value = {
            "ok": True,
            "status": "installed_with_brew",
            "app": "spotify",
            "method": "brew",
            "detail": "installed",
        }
        summary = service.dispatch(limit=10)

    assert summary.failures == 0
    assert len(summary.items) == 1
    row = service.store.get(approval_id)
    assert row is not None
    assert row["status"] == "processed"


def test_approval_service_dispatch_treats_install_app_failure_as_failed(tmp_path):
    cfg = _config(tmp_path)
    service = ApprovalService(cfg)

    approval_id = service.request(
        "install_app",
        {
            "app": "spotify",
            "method": "auto",
            "open_after_download": True,
        },
    )
    assert service.approve(approval_id)

    with patch("jarvis.approval_service.dispatch_install_app") as mock_dispatch:
        mock_dispatch.return_value = {
            "ok": False,
            "status": "install_failed",
            "error": "required executable not found",
        }
        summary = service.dispatch(limit=10)

    assert summary.failures == 1
    assert len(summary.items) == 1
    row = service.store.get(approval_id)
    assert row is not None
    assert row["status"] == "failed"


def test_approval_service_dispatch_treats_uninstall_app_success_as_processed(tmp_path):
    cfg = _config(tmp_path)
    service = ApprovalService(cfg)

    approval_id = service.request(
        "uninstall_app",
        {
            "app": "spotify",
        },
    )
    assert service.approve(approval_id)

    with patch("jarvis.approval_service.dispatch_uninstall_app") as mock_dispatch:
        mock_dispatch.return_value = {
            "ok": True,
            "status": "uninstalled",
            "app": "Spotify",
            "method": "brew_uninstall",
        }
        summary = service.dispatch(limit=10)

    assert summary.failures == 0
    assert len(summary.items) == 1
    row = service.store.get(approval_id)
    assert row is not None
    assert row["status"] == "processed"


def test_approval_service_dispatch_treats_uninstall_app_manual_fallback_as_success(tmp_path):
    cfg = _config(tmp_path)
    service = ApprovalService(cfg)

    approval_id = service.request(
        "uninstall_app",
        {
            "app": "spotify",
        },
    )
    assert service.approve(approval_id)

    with patch("jarvis.approval_service.dispatch_uninstall_app") as mock_dispatch:
        mock_dispatch.return_value = {
            "ok": True,
            "status": "manual_removal_needed",
            "app": "Spotify",
            "method": "manual",
            "directions": "Open Applications...",
        }
        summary = service.dispatch(limit=10)

    assert summary.failures == 0
    assert len(summary.items) == 1
    row = service.store.get(approval_id)
    assert row is not None
    assert row["status"] == "processed"
