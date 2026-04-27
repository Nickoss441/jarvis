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
