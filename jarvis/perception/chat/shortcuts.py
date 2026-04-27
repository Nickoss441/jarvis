"""iOS Shortcuts chat adapter scaffold for phase-2 perception."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ShortcutsChatAdapter:
    """Normalize inbound iOS Shortcuts webhook payloads."""

    source_name: str = "ios_shortcuts"

    def parse_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(payload, dict):
            return {"error": "payload must be an object"}

        sender = str(payload.get("sender") or payload.get("user") or "unknown")
        channel = str(payload.get("channel") or "shortcuts")
        text = str(payload.get("text") or payload.get("message") or "").strip()
        if not text:
            return {"error": "missing message text"}

        return {
            "kind": "chat_message",
            "source": self.source_name,
            "sender": sender,
            "channel": channel,
            "text": text,
            "metadata": {
                "shortcut_name": payload.get("shortcut_name", ""),
                "conversation_id": payload.get("conversation_id", ""),
            },
        }
