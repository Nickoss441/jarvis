"""Messaging channel strategy selection helpers."""

from __future__ import annotations

from typing import Iterable


_SUPPORTED_CHANNELS = ("sms", "imessage", "slack", "push", "email")


def choose_messaging_channel(
    *,
    primary_channel: str,
    fallback_channels: Iterable[str] = (),
    available_channels: Iterable[str] = _SUPPORTED_CHANNELS,
    strict: bool = False,
) -> dict[str, object]:
    """Choose a routing channel from preferred + fallback order."""
    available = {
        c.strip().lower()
        for c in available_channels
        if str(c).strip()
    }
    order: list[str] = []

    primary = str(primary_channel or "").strip().lower()
    if primary:
        order.append(primary)

    for channel in fallback_channels:
        normalized = str(channel or "").strip().lower()
        if normalized and normalized not in order:
            order.append(normalized)

    selected = ""
    for candidate in order:
        if candidate in available:
            selected = candidate
            break

    ok = bool(selected) or not strict
    return {
        "ok": ok,
        "strict": bool(strict),
        "primary_channel": primary,
        "fallback_channels": [c for c in order[1:]],
        "available_channels": sorted(available),
        "selected_channel": selected,
        "strategy_order": order,
        **({"error": "no_available_messaging_channel"} if strict and not selected else {}),
    }
