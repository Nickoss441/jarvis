"""Outbound calling tool with approval queue + dry-run call logger."""
import html
import json
import time
import uuid
from pathlib import Path
from typing import Any, Callable

from . import Tool

try:
    import httpx as httpx  # noqa: PLC0414
except ImportError:
    httpx = None  # type: ignore[assignment]

CALL_DISCLOSURE_TEMPLATE = (
    "Hello, this is an AI assistant calling on behalf of {user_name} "
    "to {purpose}. Is that alright to proceed?"
)


def build_call_disclosure(user_name: str | None, purpose: str | None) -> str:
    name = (user_name or "the user").strip() or "the user"
    call_purpose = (purpose or "assist with your request").strip()
    return CALL_DISCLOSURE_TEMPLATE.format(user_name=name, purpose=call_purpose)


def inject_disclosure_first_line(message: str, disclosure: str) -> str:
    """Return a call script that always starts with the disclosure line."""
    body = (message or "").strip()
    lead = (disclosure or "").strip()
    if not body:
        return lead
    if body.startswith(lead):
        return body
    return f"{lead}\n{body}"


def dispatch_call_phone(
    mode: str,
    calls_log_path: Path,
    payload: dict[str, Any],
    provider: str = "dry_run",
    caller_id: str = "",
    twilio_account_sid: str = "",
    twilio_auth_token: str = "",
    vapi_api_key: str = "",
    vapi_assistant_id: str = "",
    vapi_phone_number_id: str = "",
) -> dict[str, Any]:
    """Execute a phone call in dry-run mode."""
    mode = (mode or "dry_run").strip().lower()
    provider = (provider or "dry_run").strip().lower()
    calls_log_path = Path(calls_log_path).expanduser()

    phone_number = str(payload.get("phone_number") or "").strip()
    message = str(payload.get("message") or "").strip()
    subject = str(payload.get("subject") or "").strip()
    user_name = str(payload.get("user_name") or "").strip()
    purpose = str(payload.get("purpose") or "").strip() or subject

    if not phone_number or not message:
        return {"error": "phone_number and message are required"}

    # Validate E.164 format: + followed by 7-15 digits only
    import re as _re
    if not _re.fullmatch(r"\+\d{7,15}", phone_number):
        return {
            "error": "phone_number must be in E.164 format (e.g., +14155552671)"
        }

    disclosure = build_call_disclosure(user_name=user_name, purpose=purpose)
    script = inject_disclosure_first_line(message=message, disclosure=disclosure)
    handoff_reason = str(payload.get("handoff_reason") or "").strip()
    human_requested = bool(payload.get("human_requested")) or bool(handoff_reason)
    recording_url = ""
    transcript = ""

    if human_requested:
        call_id = str(uuid.uuid4())
        transcript = f"[handoff requested] {handoff_reason or 'recipient requested a human operator'}"
        call_record = {
            "id": call_id,
            "ts": time.time(),
            "mode": mode,
            "provider": provider,
            "phone_number": phone_number,
            "subject": subject,
            "message": message,
            "disclosure": disclosure,
            "script": script,
            "recording_url": recording_url,
            "transcript": transcript,
            "status": "human_handoff_requested",
            "handoff_reason": handoff_reason,
        }

        calls_log_path.parent.mkdir(parents=True, exist_ok=True)
        with calls_log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(call_record, sort_keys=True) + "\n")

        return {
            "status": "human_handoff_requested",
            "handoff_required": True,
            "handoff_reason": handoff_reason,
            "call_id": call_record["id"],
            "phone_number": phone_number,
            "calls_log_path": str(calls_log_path),
            "recording_url": recording_url,
            "transcript": transcript,
        }

    if mode == "dry_run":
        call_id = str(uuid.uuid4())
        recording_url = f"dry-run://call-recordings/{call_id}.wav"
        transcript = f"[dry_run transcript] {script}"
        call_record = {
            "id": call_id,
            "ts": time.time(),
            "mode": mode,
            "provider": "dry_run",
            "phone_number": phone_number,
            "subject": subject,
            "message": message,
            "disclosure": disclosure,
            "script": script,
            "recording_url": recording_url,
            "transcript": transcript,
        }

        calls_log_path.parent.mkdir(parents=True, exist_ok=True)
        with calls_log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(call_record, sort_keys=True) + "\n")

        return {
            "status": "dry_run_logged",
            "call_id": call_record["id"],
            "phone_number": phone_number,
            "calls_log_path": str(calls_log_path),
            "recording_url": recording_url,
            "transcript": transcript,
        }

    if mode != "live":
        return {
            "status": "not_implemented",
            "tool": "call_phone",
            "message": (
                f"mode '{mode}' is not implemented yet. "
                "Use JARVIS_CALL_PHONE_MODE=dry_run for scaffolding."
            ),
        }

    if provider not in {"twilio", "vapi"}:
        return {
            "status": "not_implemented",
            "tool": "call_phone",
            "message": f"provider '{provider}' is not implemented for live mode",
        }

    from_number = (caller_id or "").strip()
    if not from_number or not from_number.startswith("+") or len(from_number) < 10:
        return {"error": "caller_id must be set in E.164 format for twilio live calls"}

    if httpx is None:
        return {"error": "httpx not installed. pip install httpx"}

    if provider == "vapi":
        api_key = (vapi_api_key or "").strip()
        assistant_id = (vapi_assistant_id or "").strip() or str(payload.get("assistant_id") or "").strip()
        phone_number_id = (vapi_phone_number_id or "").strip() or str(payload.get("phone_number_id") or "").strip()

        if not api_key:
            return {"error": "vapi api key is required (VAPI_API_KEY)"}
        if not assistant_id:
            return {
                "error": (
                    "vapi assistant id is required "
                    "(JARVIS_TELEPHONY_VAPI_ASSISTANT_ID or payload.assistant_id)"
                )
            }
        if not phone_number_id:
            return {
                "error": (
                    "vapi phone number id is required "
                    "(JARVIS_TELEPHONY_VAPI_PHONE_NUMBER_ID or payload.phone_number_id)"
                )
            }

        request_body: dict[str, Any] = {
            "assistantId": assistant_id,
            "phoneNumberId": phone_number_id,
            "customer": {"number": phone_number},
            # Keep the disclosure-enforced script visible for auditability.
            "assistantOverrides": {"firstMessage": script},
            "metadata": {
                "subject": subject,
                "purpose": purpose,
                "disclosure": disclosure,
            },
        }

        try:
            resp = httpx.post(
                "https://api.vapi.ai/call",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=request_body,
                timeout=10.0,
            )
            resp.raise_for_status()
            payload_json = resp.json() if hasattr(resp, "json") else {}
        except Exception as exc:  # noqa: BLE001
            return {"error": f"vapi call failed: {exc}"}

        vapi_call_id = str(
            payload_json.get("id")
            or payload_json.get("call", {}).get("id")
            or ""
        )
        recording_url = str(payload_json.get("recordingUrl") or "")
        transcript = "[pending transcription]" if vapi_call_id else ""
        call_record = {
            "id": vapi_call_id or str(uuid.uuid4()),
            "ts": time.time(),
            "mode": mode,
            "provider": "vapi",
            "phone_number": phone_number,
            "caller_id": from_number,
            "subject": subject,
            "message": message,
            "disclosure": disclosure,
            "script": script,
            "vapi_call_id": vapi_call_id,
            "recording_url": recording_url,
            "transcript": transcript,
        }
        calls_log_path.parent.mkdir(parents=True, exist_ok=True)
        with calls_log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(call_record, sort_keys=True) + "\n")

        return {
            "status": "vapi_queued",
            "call_id": call_record["id"],
            "provider": "vapi",
            "phone_number": phone_number,
            "calls_log_path": str(calls_log_path),
            "recording_url": recording_url,
            "transcript": transcript,
        }

    sid = (twilio_account_sid or "").strip()
    token = (twilio_auth_token or "").strip()
    if not sid or not token:
        return {"error": "twilio credentials are required (TWILIO_ACCOUNT_SID/TWILIO_AUTH_TOKEN)"}

    twiml = (
        "<Response><Say>"
        + html.escape(script)
        + "</Say></Response>"
    )
    url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Calls.json"

    try:
        resp = httpx.post(
            url,
            data={
                "To": phone_number,
                "From": from_number,
                "Twiml": twiml,
            },
            auth=(sid, token),
            timeout=10.0,
        )
        resp.raise_for_status()
        payload_json = resp.json() if hasattr(resp, "json") else {}
    except Exception as exc:  # noqa: BLE001
        return {"error": f"twilio call failed: {exc}"}

    twilio_call_sid = str(payload_json.get("sid") or "")
    recording_url = (
        f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Calls/{twilio_call_sid}/Recordings.json"
        if twilio_call_sid
        else ""
    )
    transcript = (
        "[pending transcription]"
        if twilio_call_sid
        else ""
    )
    call_record = {
        "id": twilio_call_sid or str(uuid.uuid4()),
        "ts": time.time(),
        "mode": mode,
        "provider": "twilio",
        "phone_number": phone_number,
        "caller_id": from_number,
        "subject": subject,
        "message": message,
        "disclosure": disclosure,
        "script": script,
        "twilio_sid": twilio_call_sid,
        "twilio_status": str(payload_json.get("status") or "queued"),
        "recording_url": recording_url,
        "transcript": transcript,
    }
    calls_log_path.parent.mkdir(parents=True, exist_ok=True)
    with calls_log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(call_record, sort_keys=True) + "\n")

    return {
        "status": "twilio_queued",
        "call_id": call_record["id"],
        "provider": "twilio",
        "phone_number": phone_number,
        "calls_log_path": str(calls_log_path),
        "recording_url": recording_url,
        "transcript": transcript,
    }


def make_call_phone_tool(
    request_approval: Callable[[str, dict[str, Any]], str],
    get_approval: Callable[[str], dict[str, Any] | None] | None = None,
) -> Tool:
    """Create the call_phone tool with approval gating."""

    def _handler(
        phone_number: str,
        message: str,
        subject: str | None = None,
    ) -> dict[str, Any]:
        phone_number = (phone_number or "").strip()
        if not phone_number or not message.strip():
            return {"error": "phone_number and message are required"}

        import re as _re3
        if not _re3.fullmatch(r"\+\d{7,15}", phone_number):
            return {
                "error": "phone_number must be in E.164 format (e.g., +14155552671)"
            }

        approval_id = request_approval(
            "call_phone",
            {
                "phone_number": phone_number,
                "subject": subject or "",
                "message": message,
            },
        )

        approval = get_approval(approval_id) if get_approval else None

        purpose = (subject or "assist with your request").strip()
        disclosure_preview = build_call_disclosure(
            user_name="the user",
            purpose=purpose,
        )

        return {
            "status": "pending_approval",
            "approval_id": approval_id,
            "correlation_id": approval["correlation_id"] if approval else "",
            "kind": "call_phone",
            "disclosure_template": CALL_DISCLOSURE_TEMPLATE,
            "disclosure_preview": disclosure_preview,
            "message": "call queued for approval",
        }

    return Tool(
        name="call_phone",
        description=(
            "Place an outbound phone call with mandatory AI disclosure. "
            "Current implementation supports dry-run call logging."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "phone_number": {
                    "type": "string",
                    "description": "Destination phone in E.164 format (e.g., +14155552671)",
                },
                "message": {"type": "string", "description": "Call message/script"},
                "subject": {
                    "type": "string",
                    "description": "Optional call subject/reason",
                },
                "human_requested": {
                    "type": "boolean",
                    "description": "When true, request graceful handoff to a human instead of placing AI call.",
                },
                "handoff_reason": {
                    "type": "string",
                    "description": "Optional reason/details for human handoff request.",
                },
            },
            "required": ["phone_number", "message"],
        },
        handler=_handler,
        tier="gated",
    )
