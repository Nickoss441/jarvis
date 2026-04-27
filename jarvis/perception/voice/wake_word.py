"""Wake-word adapter scaffold for phase-2 voice perception."""
from __future__ import annotations

from dataclasses import dataclass


class WakeWordAdapter:
    """Adapter protocol for wake-word detection backends."""

    provider: str

    def detect_trigger(self, audio_chunk: bytes) -> bool:
        """Return True when a wake-word trigger is detected."""
        raise NotImplementedError


@dataclass
class DryRunWakeWordAdapter(WakeWordAdapter):
    """Deterministic wake-word detector used for tests/scaffolding.

    This adapter treats incoming bytes as utf-8 text and reports a trigger when
    the configured wake word appears case-insensitively.
    """

    wake_word: str = "jarvis"
    provider: str = "dry_run"

    def detect_trigger(self, audio_chunk: bytes) -> bool:
        text = audio_chunk.decode("utf-8", errors="ignore").lower()
        target = self.wake_word.strip().lower()
        if not target:
            return False
        return target in text


@dataclass
class UnsupportedWakeWordAdapter(WakeWordAdapter):
    """Placeholder adapter for providers not implemented yet."""

    provider: str

    def detect_trigger(self, audio_chunk: bytes) -> bool:
        return False


def build_wake_word_adapter(provider: str, wake_word: str) -> WakeWordAdapter:
    """Construct a wake-word adapter for the given provider."""
    normalized = (provider or "").strip().lower() or "dry_run"
    if normalized in {"dry_run", "local", "porcupine"}:
        return DryRunWakeWordAdapter(wake_word=wake_word)
    return UnsupportedWakeWordAdapter(provider=normalized)
