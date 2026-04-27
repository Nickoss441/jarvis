"""Wake-word listener runtime helper."""
from __future__ import annotations

from dataclasses import dataclass

from .wake_word import WakeWordAdapter


@dataclass
class WakeWordListener:
    """Stateful wake-word ingestion helper for byte chunks."""

    adapter: WakeWordAdapter
    chunks_seen: int = 0
    triggers: int = 0

    def ingest(self, audio_chunk: bytes) -> dict[str, object]:
        self.chunks_seen += 1
        triggered = bool(self.adapter.detect_trigger(audio_chunk))
        if triggered:
            self.triggers += 1
        return {
            "triggered": triggered,
            "chunks_seen": self.chunks_seen,
            "triggers": self.triggers,
            "provider": getattr(self.adapter, "provider", "unknown"),
        }