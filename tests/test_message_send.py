import json

from jarvis.approval import ApprovalStore
from jarvis.tools.message_send import dispatch_message_send, make_message_send_tool


def test_message_send_queues_pending_approval(tmp_path):
    store = ApprovalStore(tmp_path / "approvals.db")
    tool = make_message_send_tool(
        request_approval=store.request,
        get_approval=store.get,
    )

    result = tool.handler(
        channel="email",
        recipient="user@example.com",
        subject="Hi",
        body="Hello from Jarvis",
    )

    assert result["status"] == "pending_approval"
    approval = store.get(result["approval_id"])
    assert approval is not None
    assert approval["status"] == "pending"
    assert approval["kind"] == "message_send"
    assert approval["payload"]["channel"] == "email"
    assert approval["payload"]["recipient"] == "user@example.com"
    assert result["correlation_id"] == approval["correlation_id"]
    assert result["correlation_id"]


def test_dispatch_message_send_dry_run_writes_outbox(tmp_path):
    outbox = tmp_path / "outbox.jsonl"
    result = dispatch_message_send(
        mode="dry_run",
        outbox_path=outbox,
        payload={
            "channel": "email",
            "recipient": "user@example.com",
            "subject": "Hi",
            "body": "Hello from Jarvis",
        },
    )

    assert result["status"] == "dry_run_sent"

    lines = outbox.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    event = json.loads(lines[0])
    assert event["channel"] == "email"
    assert event["recipient"] == "user@example.com"
    assert event["subject"] == "Hi"
    assert event["body"] == "Hello from Jarvis"


def test_dispatch_message_send_rejects_unsupported_channel(tmp_path):
    result = dispatch_message_send(
        mode="dry_run",
        outbox_path=tmp_path / "outbox.jsonl",
        payload={
            "channel": "fax",
            "recipient": "123",
            "body": "nope",
        },
    )

    assert "error" in result
    assert "unsupported channel" in result["error"]


def test_dispatch_message_send_non_dry_run_returns_not_implemented(tmp_path):
    result = dispatch_message_send(
        mode="twilio",
        outbox_path=tmp_path / "outbox.jsonl",
        payload={
            "channel": "sms",
            "recipient": "+15551234567",
            "body": "hello",
        },
    )

    assert result["status"] == "not_implemented"
    assert result["tool"] == "message_send"
