"""Speech-to-text adapter scaffold for phase-2 voice perception."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class STTAdapter:
    """Adapter protocol for speech-to-text backends."""

    provider: str

    def transcribe(self, audio_bytes: bytes, language: str = "en") -> dict[str, Any]:
        """Convert speech audio to text."""
        raise NotImplementedError


@dataclass
class DryRunSTTAdapter(STTAdapter):
    """Deterministic STT adapter for tests and local scaffolding."""

    provider: str = "faster-whisper"

    def transcribe(self, audio_bytes: bytes, language: str = "en") -> dict[str, Any]:
        text = audio_bytes.decode("utf-8", errors="ignore").strip()
        if not text:
            text = "[dry_run transcript]"
        return {
            "provider": self.provider,
            "language": language,
            "text": text,
            "confidence": 1.0,
        }


@dataclass
class UnsupportedSTTAdapter(STTAdapter):
    """Placeholder adapter for providers not implemented yet."""

    provider: str

    def transcribe(self, audio_bytes: bytes, language: str = "en") -> dict[str, Any]:
        return {
            "provider": self.provider,
            "language": language,
            "text": "",
            "confidence": 0.0,
            "error": f"stt provider '{self.provider}' not implemented",
        }


def build_stt_adapter(provider: str) -> STTAdapter:
    """Construct an STT adapter for the configured provider."""
    normalized = (provider or "").strip().lower() or "faster-whisper"
    if normalized in {"faster-whisper", "dry_run", "whisperx"}:
        return DryRunSTTAdapter(provider=normalized)
    return UnsupportedSTTAdapter(provider=normalized)
