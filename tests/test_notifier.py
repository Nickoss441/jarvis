"""Tests for push notifier adapters."""
import pytest
from unittest.mock import MagicMock, patch

from jarvis.notifier import (
    LogNotifier,
    NtfyNotifier,
    PushNotifier,
    build_notifier,
)


# ── interface contract ─────────────────────────────────────────────────────────

def test_log_notifier_implements_interface():
    assert isinstance(LogNotifier(), PushNotifier)


def test_ntfy_notifier_implements_interface():
    assert isinstance(NtfyNotifier(topic="test"), PushNotifier)


# ── LogNotifier ────────────────────────────────────────────────────────────────

def test_log_notifier_returns_not_sent():
    notifier = LogNotifier()
    result = notifier.notify("id-1", "message_send", {"channel": "slack"})
    assert result["sent"] is False
    assert result["channel"] == "log"


def test_log_notifier_accepts_empty_payload():
    notifier = LogNotifier()
    result = notifier.notify("id-2", "trade", {})
    assert result["sent"] is False


# ── NtfyNotifier message builder ──────────────────────────────────────────────

def test_ntfy_message_includes_kind_and_known_keys():
    n = NtfyNotifier(topic="t")
    msg = n._build_message("message_send", {"channel": "slack", "recipient": "@bob"})
    assert "message_send" in msg
    assert "channel=slack" in msg
    assert "recipient=@bob" in msg


def test_ntfy_message_falls_back_to_first_keys():
    n = NtfyNotifier(topic="t")
    msg = n._build_message("custom_kind", {"foo": "bar", "baz": 1})
    assert "custom_kind" in msg
    assert "foo=bar" in msg


def test_ntfy_message_empty_payload_returns_kind_only():
    n = NtfyNotifier(topic="t")
    msg = n._build_message("trade", {})
    assert msg == "trade"


# ── NtfyNotifier headers ──────────────────────────────────────────────────────

def test_ntfy_headers_no_token():
    n = NtfyNotifier(topic="jarvis-approvals", priority="high")
    headers = n._build_headers()
    assert headers["Title"] == "Jarvis approval [medium]"
    assert headers["Priority"] == "high"
    assert "Authorization" not in headers


def test_ntfy_headers_with_token():
    n = NtfyNotifier(topic="jarvis-approvals", token="secret123")
    headers = n._build_headers()
    assert headers["Authorization"] == "Bearer secret123"


# ── NtfyNotifier no topic guard ───────────────────────────────────────────────

def test_ntfy_empty_topic_returns_not_sent():
    n = NtfyNotifier(topic="")
    result = n.notify("id-1", "message_send", {})
    assert result["sent"] is False
    assert result["reason"] == "no_topic"


# ── NtfyNotifier live send (mocked httpx) ─────────────────────────────────────

def test_ntfy_sends_post_on_notify():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.raise_for_status = MagicMock()

    with patch("jarvis.notifier.httpx") as mock_httpx:
        mock_httpx.post.return_value = mock_resp

        n = NtfyNotifier(topic="jarvis-approvals", ntfy_url="https://ntfy.sh")
        result = n.notify("appr-1", "message_send", {"channel": "slack"})

    assert result["sent"] is True
    assert result["channel"] == "ntfy"
    assert result["topic"] == "jarvis-approvals"
    assert result["status_code"] == 200

    mock_httpx.post.assert_called_once()
    call_kwargs = mock_httpx.post.call_args
    assert "jarvis-approvals" in call_kwargs[0][0]


def test_ntfy_returns_not_sent_on_http_error():
    with patch("jarvis.notifier.httpx") as mock_httpx:
        mock_httpx.post.side_effect = Exception("connection refused")

        n = NtfyNotifier(topic="jarvis-approvals")
        result = n.notify("appr-2", "trade", {})

    assert result["sent"] is False
    assert "error" in result


def test_ntfy_missing_httpx_returns_not_sent():
    n = NtfyNotifier(topic="jarvis-approvals")
    with patch("jarvis.notifier.httpx", None):
        result = n.notify("appr-3", "message_send", {})
    assert result["sent"] is False
    assert result["reason"] == "httpx_missing"


# ── build_notifier factory ─────────────────────────────────────────────────────

def test_build_notifier_ntfy_with_topic_returns_ntfy():
    notifier = build_notifier(channel="ntfy", ntfy_topic="my-topic")
    assert isinstance(notifier, NtfyNotifier)


def test_build_notifier_ntfy_without_topic_falls_back_to_log():
    notifier = build_notifier(channel="ntfy", ntfy_topic="")
    assert isinstance(notifier, LogNotifier)


def test_build_notifier_unknown_channel_returns_log():
    notifier = build_notifier(channel="pushover", ntfy_topic="")
    assert isinstance(notifier, LogNotifier)


def test_build_notifier_disabled_channel_returns_log():
    notifier = build_notifier(channel="disabled")
    assert isinstance(notifier, LogNotifier)


# ── ApprovalService integration ────────────────────────────────────────────────

def test_approval_service_calls_notifier_on_request(tmp_path):
    """ApprovalService.request() triggers the notifier."""
    from unittest.mock import MagicMock
    from jarvis.approval_service import ApprovalService
    from jarvis.config import Config

    config = Config(
        anthropic_api_key="x",
        model="claude-sonnet-4-6",
        notes_dir=tmp_path / "notes",
        audit_db=tmp_path / "audit.db",
        user_name="Test",
        approval_db=tmp_path / "approvals.db",
        approval_channel="ntfy",
        ntfy_topic="",  # falls back to LogNotifier
    )

    service = ApprovalService(config)

    mock_notifier = MagicMock()
    mock_notifier.notify.return_value = {"sent": True, "channel": "ntfy"}
    service._notifier = mock_notifier

    approval_id = service.request("message_send", {"channel": "slack", "body": "hi"})

    mock_notifier.notify.assert_called_once()
    call_args = mock_notifier.notify.call_args[0]
    assert call_args[0] == approval_id
    assert call_args[1] == "message_send"


def test_approval_service_continues_if_notifier_fails(tmp_path):
    """A notifier exception must not break ApprovalService.request()."""
    from jarvis.approval_service import ApprovalService
    from jarvis.config import Config

    config = Config(
        anthropic_api_key="x",
        model="claude-sonnet-4-6",
        notes_dir=tmp_path / "notes",
        audit_db=tmp_path / "audit.db",
        user_name="Test",
        approval_db=tmp_path / "approvals.db",
        ntfy_topic="",
    )

    service = ApprovalService(config)

    mock_notifier = MagicMock()
    mock_notifier.notify.side_effect = RuntimeError("push service down")
    service._notifier = mock_notifier

    # Should not raise
    approval_id = service.request("trade", {"symbol": "SOL"})
    assert approval_id  # returned an ID despite notifier failure
