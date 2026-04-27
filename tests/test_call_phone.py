"""Tests for call_phone tool and dispatcher."""
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from jarvis.tools.call_phone import (
    CALL_DISCLOSURE_TEMPLATE,
    build_call_disclosure,
    dispatch_call_phone,
    inject_disclosure_first_line,
    make_call_phone_tool,
)


def test_call_disclosure_template_is_frozen():
    assert CALL_DISCLOSURE_TEMPLATE == (
        "Hello, this is an AI assistant calling on behalf of {user_name} "
        "to {purpose}. Is that alright to proceed?"
    )


def test_build_call_disclosure_uses_expected_defaults():
    disclosure = build_call_disclosure(user_name="", purpose="")

    assert disclosure == (
        "Hello, this is an AI assistant calling on behalf of the user "
        "to assist with your request. Is that alright to proceed?"
    )


def test_inject_disclosure_first_line_prepends_disclosure():
    disclosure = build_call_disclosure(user_name="Nick", purpose="confirm a booking")
    script = inject_disclosure_first_line(
        message="I am calling to confirm your reservation.",
        disclosure=disclosure,
    )

    assert script.splitlines()[0] == disclosure
    assert "confirm your reservation" in script


def test_inject_disclosure_first_line_is_idempotent():
    disclosure = build_call_disclosure(user_name="Nick", purpose="confirm a booking")
    script = inject_disclosure_first_line(
        message=f"{disclosure}\nI am calling to confirm your reservation.",
        disclosure=disclosure,
    )

    assert script.count(disclosure) == 1


def test_dispatch_call_phone_dry_run(tmp_path):
    """Test dry-run call logging."""
    calls_log = tmp_path / "calls.jsonl"
    result = dispatch_call_phone(
        mode="dry_run",
        calls_log_path=calls_log,
        payload={
            "phone_number": "+14155552671",
            "subject": "Test call",
            "message": "Hello, this is a test",
        },
    )

    assert result["status"] == "dry_run_logged"
    assert result["phone_number"] == "+14155552671"
    assert calls_log.exists()

    # Verify log contents
    logged = json.loads(calls_log.read_text())
    assert logged["phone_number"] == "+14155552671"
    assert logged["message"] == "Hello, this is a test"
    assert logged["mode"] == "dry_run"
    assert logged["disclosure"] == (
        "Hello, this is an AI assistant calling on behalf of the user "
        "to Test call. Is that alright to proceed?"
    )
    assert logged["script"].splitlines()[0] == logged["disclosure"]
    assert logged["script"].endswith("Hello, this is a test")
    assert logged["recording_url"].startswith("dry-run://call-recordings/")
    assert logged["transcript"].startswith("[dry_run transcript] ")
    assert result["recording_url"].startswith("dry-run://call-recordings/")
    assert result["transcript"].startswith("[dry_run transcript] ")


def test_dispatch_call_phone_missing_phone_number(tmp_path):
    """Test that missing phone_number returns an error."""
    calls_log = tmp_path / "calls.jsonl"
    result = dispatch_call_phone(
        mode="dry_run",
        calls_log_path=calls_log,
        payload={
            "message": "Hello",
        },
    )

    assert "error" in result


def test_dispatch_call_phone_invalid_format(tmp_path):
    """Test that invalid phone format returns an error."""
    calls_log = tmp_path / "calls.jsonl"
    result = dispatch_call_phone(
        mode="dry_run",
        calls_log_path=calls_log,
        payload={
            "phone_number": "1234",
            "message": "Hello",
        },
    )

    assert "error" in result
    assert "E.164" in result["error"]


def test_make_call_phone_tool_with_approval():
    """Test call_phone tool factory with approval gating."""
    approval_store = {}

    def mock_request_approval(kind, payload):
        aid = "approval-123"
        approval_store[aid] = {
            "id": aid,
            "kind": kind,
            "payload": payload,
            "correlation_id": "corr-456",
        }
        return aid

    def mock_get_approval(aid):
        return approval_store.get(aid)

    tool = make_call_phone_tool(
        request_approval=mock_request_approval,
        get_approval=mock_get_approval,
    )

    assert tool.name == "call_phone"
    assert tool.tier == "gated"

    result = tool.handler(
        phone_number="+14155552671",
        message="Test call",
    )

    assert result["status"] == "pending_approval"
    assert result["kind"] == "call_phone"
    assert result["correlation_id"] == "corr-456"
    assert result["disclosure_template"] == CALL_DISCLOSURE_TEMPLATE
    assert result["disclosure_preview"] == (
        "Hello, this is an AI assistant calling on behalf of the user "
        "to assist with your request. Is that alright to proceed?"
    )
    assert "approval-123" in approval_store


def test_make_call_phone_tool_invalid_phone():
    """Test that invalid phone_number is rejected at tool level."""
    def mock_request_approval(kind, payload):
        return "aid-123"

    tool = make_call_phone_tool(
        request_approval=mock_request_approval,
    )

    result = tool.handler(
        phone_number="invalid",
        message="Test call",
    )

    assert "error" in result
    assert "E.164" in result["error"]


def test_dispatch_call_phone_live_twilio_missing_credentials(tmp_path):
    calls_log = tmp_path / "calls.jsonl"
    result = dispatch_call_phone(
        mode="live",
        calls_log_path=calls_log,
        payload={
            "phone_number": "+14155552671",
            "message": "Hello",
        },
        provider="twilio",
        caller_id="+14155550000",
        twilio_account_sid="",
        twilio_auth_token="",
    )

    assert "error" in result
    assert "twilio credentials" in result["error"]


def test_dispatch_call_phone_live_unknown_provider_not_implemented(tmp_path):
    calls_log = tmp_path / "calls.jsonl"
    result = dispatch_call_phone(
        mode="live",
        calls_log_path=calls_log,
        payload={
            "phone_number": "+14155552671",
            "message": "Hello",
        },
        provider="other",
    )

    assert result["status"] == "not_implemented"
    assert "provider 'other'" in result["message"]


def test_dispatch_call_phone_live_vapi_missing_required_fields(tmp_path):
    calls_log = tmp_path / "calls.jsonl"
    result = dispatch_call_phone(
        mode="live",
        calls_log_path=calls_log,
        payload={
            "phone_number": "+14155552671",
            "message": "Hello",
        },
        provider="vapi",
        caller_id="+14155550000",
        vapi_api_key="",
        vapi_assistant_id="",
        vapi_phone_number_id="",
    )

    assert "error" in result
    assert "vapi api key" in result["error"].lower()


def test_dispatch_call_phone_human_requested_graceful_handoff(tmp_path):
    calls_log = tmp_path / "calls.jsonl"
    result = dispatch_call_phone(
        mode="live",
        calls_log_path=calls_log,
        payload={
            "phone_number": "+14155552671",
            "subject": "Reminder",
            "message": "Hello",
            "human_requested": True,
            "handoff_reason": "recipient asked for a person",
        },
        provider="twilio",
    )

    assert result["status"] == "human_handoff_requested"
    assert result["handoff_required"] is True
    assert result["handoff_reason"] == "recipient asked for a person"
    assert result["transcript"].startswith("[handoff requested]")
    assert calls_log.exists()

    logged = json.loads(calls_log.read_text())
    assert logged["status"] == "human_handoff_requested"
    assert logged["handoff_reason"] == "recipient asked for a person"


def test_dispatch_call_phone_live_twilio_success(tmp_path):
    calls_log = tmp_path / "calls.jsonl"

    fake_resp = MagicMock()
    fake_resp.raise_for_status = MagicMock()
    fake_resp.json.return_value = {"sid": "CA123", "status": "queued"}

    with patch("jarvis.tools.call_phone.httpx") as mock_httpx:
        mock_httpx.post.return_value = fake_resp

        result = dispatch_call_phone(
            mode="live",
            calls_log_path=calls_log,
            payload={
                "phone_number": "+14155552671",
                "message": "Hello from Jarvis",
                "subject": "Appointment",
            },
            provider="twilio",
            caller_id="+14155550000",
            twilio_account_sid="AC123",
            twilio_auth_token="token123",
        )

    assert result["status"] == "twilio_queued"
    assert result["provider"] == "twilio"
    assert result["call_id"] == "CA123"
    assert "Calls/CA123/Recordings.json" in result["recording_url"]
    assert result["transcript"] == "[pending transcription]"
    assert calls_log.exists()

    logged = json.loads(calls_log.read_text())
    assert logged["provider"] == "twilio"
    assert logged["twilio_sid"] == "CA123"
    assert logged["caller_id"] == "+14155550000"
    assert "Calls/CA123/Recordings.json" in logged["recording_url"]
    assert logged["transcript"] == "[pending transcription]"

    mock_httpx.post.assert_called_once()


def test_dispatch_call_phone_live_vapi_success(tmp_path):
    calls_log = tmp_path / "calls.jsonl"

    fake_resp = MagicMock()
    fake_resp.raise_for_status = MagicMock()
    fake_resp.json.return_value = {"id": "call_vapi_123", "recordingUrl": "https://example.test/recording.wav"}

    with patch("jarvis.tools.call_phone.httpx") as mock_httpx:
        mock_httpx.post.return_value = fake_resp

        result = dispatch_call_phone(
            mode="live",
            calls_log_path=calls_log,
            payload={
                "phone_number": "+14155552671",
                "message": "Hello from Jarvis",
                "subject": "Appointment",
            },
            provider="vapi",
            caller_id="+14155550000",
            vapi_api_key="vapi-key",
            vapi_assistant_id="assistant-123",
            vapi_phone_number_id="phone-123",
        )

    assert result["status"] == "vapi_queued"
    assert result["provider"] == "vapi"
    assert result["call_id"] == "call_vapi_123"
    assert result["recording_url"] == "https://example.test/recording.wav"
    assert result["transcript"] == "[pending transcription]"
    assert calls_log.exists()

    logged = json.loads(calls_log.read_text())
    assert logged["provider"] == "vapi"
    assert logged["vapi_call_id"] == "call_vapi_123"
    assert logged["recording_url"] == "https://example.test/recording.wav"
    assert logged["transcript"] == "[pending transcription]"

    mock_httpx.post.assert_called_once()
