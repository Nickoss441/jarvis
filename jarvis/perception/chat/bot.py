"""Bot adapter scaffold for chat-based perception inputs."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class BotChatAdapter:
    """Normalize inbound bot/webhook chat payloads into a shared event shape."""

    source_name: str = "bot"

    def parse_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(payload, dict):
            return {"error": "payload must be an object"}

        user = str(payload.get("user") or payload.get("sender") or "unknown")
        channel = str(payload.get("channel") or payload.get("chat_id") or "bot")
        text = str(payload.get("text") or payload.get("body") or "").strip()
        if not text:
            return {"error": "missing message text"}

        return {
            "kind": "chat_message",
            "source": self.source_name,
            "sender": user,
            "channel": channel,
            "text": text,
            "metadata": {
                "message_id": payload.get("message_id", ""),
                "thread_id": payload.get("thread_id", ""),
            },
        }


def extract_command(text: str) -> dict[str, Any]:
    """Extract a slash command from user text when present.

    Examples:
      "/status" -> {"command": "status", "args": []}
      "/pay 42" -> {"command": "pay", "args": ["42"]}
    """
    value = (text or "").strip()
    if not value.startswith("/"):
        return {"command": "", "args": []}

    parts = value[1:].split()
    if not parts:
        return {"command": "", "args": []}
    return {"command": parts[0].lower(), "args": parts[1:]}


def parse_sms_command(text: str) -> dict[str, Any]:
    """Parse common SMS command forms into a normalized command object.

    Recognized intents:
      - approve <approval_id> [reason...]
      - reject <approval_id> [reason...]
      - status [approval_id]
      - approvals / list approvals
      - help
    """
    raw = (text or "").strip()
    if not raw:
        return {"recognized": False, "intent": "", "raw": raw}

    slash = extract_command(raw)
    if slash["command"]:
        tokens = [slash["command"], *slash["args"]]
    else:
        tokens = raw.split()
    lowered = [part.strip().lower() for part in tokens if part.strip()]
    if not lowered:
        return {"recognized": False, "intent": "", "raw": raw}

    cmd = lowered[0]

    if cmd in {"approve", "yes"}:
        approval_id = tokens[1].strip() if len(tokens) >= 2 else ""
        reason = " ".join(tokens[2:]).strip() if len(tokens) >= 3 else ""
        if approval_id:
            return {
                "recognized": True,
                "intent": "approve",
                "approval_id": approval_id,
                "reason": reason,
                "raw": raw,
            }

    if cmd in {"reject", "deny", "no"}:
        approval_id = tokens[1].strip() if len(tokens) >= 2 else ""
        reason = " ".join(tokens[2:]).strip() if len(tokens) >= 3 else ""
        if approval_id:
            return {
                "recognized": True,
                "intent": "reject",
                "approval_id": approval_id,
                "reason": reason,
                "raw": raw,
            }

    if cmd == "status":
        approval_id = tokens[1].strip() if len(tokens) >= 2 else ""
        return {
            "recognized": True,
            "intent": "status",
            "approval_id": approval_id,
            "raw": raw,
        }

    if cmd in {"approvals", "list"}:
        if cmd == "approvals" or (len(lowered) >= 2 and lowered[1] in {"approvals", "pending"}):
            return {
                "recognized": True,
                "intent": "list_approvals",
                "raw": raw,
            }

    if cmd in {"help", "commands"}:
        return {
            "recognized": True,
            "intent": "help",
            "raw": raw,
        }

    return {"recognized": False, "intent": "", "raw": raw}
