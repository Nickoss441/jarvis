"""Speech-to-text adapters for Jarvis voice perception."""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


class STTAdapter:
    """Adapter protocol for speech-to-text backends."""

    provider: str

    def transcribe(self, audio_bytes: bytes, language: str = "en") -> dict[str, Any]:
        """Convert speech audio to text. audio_bytes must be raw PCM s16le at 16 kHz."""
        raise NotImplementedError


@dataclass
class FasterWhisperSTTAdapter(STTAdapter):
    """Real STT adapter backed by the faster-whisper library."""

    model_size: str = "base"
    device: str = "cpu"
    compute_type: str = "int8"
    provider: str = "faster-whisper"
    _model: Any = field(default=None, init=False, repr=False)

    def _load_model(self) -> Any:
        if self._model is None:
            from faster_whisper import WhisperModel  # lazy: optional dep
            logger.info("Loading faster-whisper model '%s'...", self.model_size)
            self._model = WhisperModel(
                self.model_size, device=self.device, compute_type=self.compute_type
            )
            logger.info("faster-whisper model ready.")
        return self._model

    def transcribe(self, audio_bytes: bytes, language: str = "en") -> dict[str, Any]:
        try:
            import numpy as np
            model = self._load_model()
            # audio_bytes is raw PCM s16le at 16 000 Hz from speech_recognition
            audio_np = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0
            segments, info = model.transcribe(audio_np, beam_size=5, language=language)
            text = " ".join(seg.text for seg in segments).strip()
            return {
                "provider": self.provider,
                "language": info.language,
                "text": text,
                "confidence": float(info.language_probability),
            }
        except Exception as exc:
            return {
                "provider": self.provider,
                "language": language,
                "text": "",
                "confidence": 0.0,
                "error": f"faster-whisper transcription failed: {exc}",
            }


@dataclass
class DryRunSTTAdapter(STTAdapter):
    """Deterministic STT adapter for tests and local scaffolding."""

    provider: str = "dry_run"

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
    if normalized == "faster-whisper":
        model_size = os.getenv("JARVIS_WHISPER_MODEL", "base")
        return FasterWhisperSTTAdapter(model_size=model_size)
    if normalized in {"dry_run", "whisperx"}:
        return DryRunSTTAdapter(provider=normalized)
    return UnsupportedSTTAdapter(provider=normalized)
