"""Outbound messaging tool with approval queue + dry-run dispatcher."""
import json
import time
import uuid
from pathlib import Path
from typing import Any, Callable

from . import Tool

_ALLOWED_CHANNELS = {"email", "sms", "imessage", "slack", "push"}
_CHANNEL_ACTION = {
    "email": "email_send",
    "sms": "sms_send",
    "imessage": "imessage_send",
    "slack": "slack_send",
    "push": "push_send",
}


def dispatch_message_send(
    mode: str,
    outbox_path: Path,
    payload: dict[str, Any],
) -> dict[str, Any]:
    mode = (mode or "dry_run").strip().lower()
    outbox_path = Path(outbox_path).expanduser()

    channel_normalized = (payload.get("channel") or "").strip().lower()
    recipient = str(payload.get("recipient") or "")
    body = str(payload.get("body") or "")
    subject = str(payload.get("subject") or "")

    if channel_normalized not in _ALLOWED_CHANNELS:
        return {
            "error": (
                "unsupported channel. allowed: "
                + ", ".join(sorted(_ALLOWED_CHANNELS))
            )
        }

    if not recipient.strip() or not body.strip():
        return {"error": "recipient and body are required"}

    if mode != "dry_run":
        return {
            "status": "not_implemented",
            "tool": "message_send",
            "message": (
                f"mode '{mode}' is not implemented yet. "
                "Use JARVIS_MESSAGE_SEND_MODE=dry_run for scaffolding."
            ),
        }

    event = {
        "id": str(uuid.uuid4()),
        "ts": time.time(),
        "mode": mode,
        "channel": channel_normalized,
        "action": _CHANNEL_ACTION.get(channel_normalized, "message_send"),
        "recipient": recipient,
        "subject": subject,
        "body": body,
    }

    outbox_path.parent.mkdir(parents=True, exist_ok=True)
    with outbox_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, sort_keys=True) + "\n")

    return {
        "status": "dry_run_sent",
        "message_id": event["id"],
        "channel": event["channel"],
        "action": event["action"],
        "recipient": event["recipient"],
        "outbox_path": str(outbox_path),
    }


def make_message_send_tool(
    request_approval: Callable[[str, dict[str, Any]], str],
    get_approval: Callable[[str], dict[str, Any] | None] | None = None,
) -> Tool:

    def _handler(
        channel: str,
        recipient: str,
        body: str,
        subject: str | None = None,
    ) -> dict[str, Any]:
        channel_normalized = (channel or "").strip().lower()
        if channel_normalized not in _ALLOWED_CHANNELS:
            return {
                "error": (
                    "unsupported channel. allowed: "
                    + ", ".join(sorted(_ALLOWED_CHANNELS))
                )
            }

        if not recipient.strip() or not body.strip():
            return {"error": "recipient and body are required"}

        approval_id = request_approval(
            "message_send",
            {
                "channel": channel_normalized,
                "recipient": recipient,
                "subject": subject or "",
                "body": body,
            },
        )

        approval = get_approval(approval_id) if get_approval else None

        return {
            "status": "pending_approval",
            "approval_id": approval_id,
            "correlation_id": approval["correlation_id"] if approval else "",
            "kind": "message_send",
            "message": "queued for approval",
        }

    return Tool(
        name="message_send",
        description=(
            "Send outbound messages (email/SMS/iMessage/chat). "
            "Current implementation supports dry-run outbox delivery."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "channel": {
                    "type": "string",
                    "description": "Message channel: email, sms, imessage, slack, or push",
                },
                "recipient": {
                    "type": "string",
                    "description": "Destination address, phone number, or user ID",
                },
                "body": {"type": "string", "description": "Message body"},
                "subject": {
                    "type": "string",
                    "description": "Optional subject line (mainly for email)",
                },
            },
            "required": ["channel", "recipient", "body"],
        },
        handler=_handler,
        tier="gated",
    )
