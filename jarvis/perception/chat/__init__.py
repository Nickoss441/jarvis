"""Chat perception scaffold (iOS Shortcuts + bot adapters)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .bot import BotChatAdapter, extract_command, parse_sms_command
from .shortcuts import ShortcutsChatAdapter


@dataclass
class ChatAdapterRegistry:
    """Simple registry holding available chat adapters for phase-2."""

    shortcuts: ShortcutsChatAdapter
    bot: BotChatAdapter

    def parse(self, source: str, payload: dict[str, Any]) -> dict[str, Any]:
        kind = (source or "").strip().lower()
        if kind in {"shortcuts", "ios_shortcuts", "ios", "web_ui", "web"}:
            return self.shortcuts.parse_payload(payload)
        if kind in {"bot", "telegram", "slack"}:
            return self.bot.parse_payload(payload)
        return {"error": f"unknown chat source '{source}'"}


def build_chat_registry() -> ChatAdapterRegistry:
    """Build the default chat adapter scaffold registry."""
    return ChatAdapterRegistry(
        shortcuts=ShortcutsChatAdapter(),
        bot=BotChatAdapter(),
    )


__all__ = [
    "ShortcutsChatAdapter",
    "BotChatAdapter",
    "ChatAdapterRegistry",
    "extract_command",
    "parse_sms_command",
    "build_chat_registry",
]
