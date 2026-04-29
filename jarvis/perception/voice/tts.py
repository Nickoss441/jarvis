"""Text-to-speech adapter scaffold for phase-2 voice perception."""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any
from urllib import error as urllib_error
from urllib import request as urllib_request


class TTSAdapter:
    """Adapter protocol for text-to-speech backends."""

    provider: str

    def synthesize(self, text: str, voice: str = "default") -> dict[str, Any]:
        """Synthesize speech audio from text."""
        raise NotImplementedError


@dataclass
class DryRunTTSAdapter(TTSAdapter):
    """Deterministic TTS adapter for tests and local scaffolding."""

    provider: str = "piper"

    def synthesize(self, text: str, voice: str = "default") -> dict[str, Any]:
        payload = text.encode("utf-8", errors="ignore")
        return {
            "provider": self.provider,
            "voice": voice,
            "audio": payload,
            "sample_rate_hz": 16000,
            "format": "pcm_s16le",
        }


@dataclass
class UnsupportedTTSAdapter(TTSAdapter):
    """Placeholder adapter for providers not implemented yet."""

    provider: str

    def synthesize(self, text: str, voice: str = "default") -> dict[str, Any]:
        return {
            "provider": self.provider,
            "voice": voice,
            "audio": b"",
            "sample_rate_hz": 0,
            "format": "unknown",
            "error": f"tts provider '{self.provider}' not implemented",
        }


@dataclass
class PiperLocalTTSAdapter(TTSAdapter):
    """Local Piper adapter backed by ONNX voice files."""

    voice_ids: dict[str, str] | None = None
    default_voice: str = "male"
    download_dir: Path = Path("D:/DATASET/voices")
    provider: str = "piper"

    def __post_init__(self) -> None:
        self._voice_cache: dict[str, Any] = {}

    def _resolve_model_spec(self, voice: str) -> tuple[str, str]:
        aliases = self.voice_ids or {}
        requested = (voice or "").strip().lower() or self.default_voice
        if requested in {"assistant", "default"}:
            requested = self.default_voice
        if requested in aliases and aliases[requested].strip():
            return requested, aliases[requested].strip()
        if requested in {"male", "m"}:
            return requested, "en_US-ryan-medium"
        if requested in {"female", "f"}:
            return requested, "en_US-amy-medium"
        return requested, requested

    def _resolve_paths(self, model_spec: str) -> tuple[Path, Path | None]:
        spec = model_spec.strip()
        spec_path = Path(spec)
        if spec_path.is_absolute() and spec_path.exists():
            model_path = spec_path
        else:
            if not spec.endswith(".onnx"):
                spec = f"{spec}.onnx"
            model_path = self.download_dir / spec
        config_path = Path(f"{model_path}.json")
        return model_path, (config_path if config_path.exists() else None)

    def _load_voice(self, model_path: Path, config_path: Path | None) -> Any:
        cache_key = str(model_path.resolve())
        if cache_key in self._voice_cache:
            return self._voice_cache[cache_key]
        from piper.voice import PiperVoice  # Lazy import for optional dependency.

        voice = PiperVoice.load(model_path=model_path, config_path=config_path)
        self._voice_cache[cache_key] = voice
        return voice

    def synthesize(self, text: str, voice: str = "default") -> dict[str, Any]:
        requested_voice, model_spec = self._resolve_model_spec(voice)
        message = (text or "").strip()
        if not message:
            return {
                "provider": self.provider,
                "voice": requested_voice,
                "audio": b"",
                "sample_rate_hz": 0,
                "format": "unknown",
                "error": "text is required",
            }

        model_path, config_path = self._resolve_paths(model_spec)
        if not model_path.exists():
            return {
                "provider": self.provider,
                "voice": requested_voice,
                "audio": b"",
                "sample_rate_hz": 0,
                "format": "unknown",
                "error": f"piper voice model not found: {model_path}",
            }

        try:
            local_voice = self._load_voice(model_path, config_path)
            chunks = list(local_voice.synthesize(message))
            if not chunks:
                return {
                    "provider": self.provider,
                    "voice": requested_voice,
                    "audio": b"",
                    "sample_rate_hz": 0,
                    "format": "unknown",
                    "error": "piper synthesis produced no audio",
                }
            audio = b"".join(chunk.audio_int16_bytes for chunk in chunks)
            sample_rate = int(getattr(chunks[0], "sample_rate", 22050) or 22050)
            return {
                "provider": self.provider,
                "voice": requested_voice,
                "model": str(model_path),
                "audio": audio,
                "sample_rate_hz": sample_rate,
                "format": "pcm_s16le",
            }
        except Exception as exc:
            return {
                "provider": self.provider,
                "voice": requested_voice,
                "audio": b"",
                "sample_rate_hz": 0,
                "format": "unknown",
                "error": f"piper synthesis failed: {exc}",
            }


@dataclass
class FallbackTTSAdapter(TTSAdapter):
    """Wrap a primary adapter and fall back when synthesis fails."""

    primary: TTSAdapter
    fallback: TTSAdapter
    provider: str = "fallback"

    def synthesize(self, text: str, voice: str = "default") -> dict[str, Any]:
        primary_out = self.primary.synthesize(text, voice=voice)
        if not primary_out.get("error"):
            return primary_out

        fallback_out = self.fallback.synthesize(text, voice=voice)
        fallback_out["fallback_from"] = self.primary.provider
        fallback_out["fallback_reason"] = str(primary_out.get("error") or "primary_failed")
        return fallback_out


@dataclass
class ElevenLabsTTSAdapter(TTSAdapter):
    """HTTP-backed ElevenLabs adapter with male/female voice profile support."""

    api_key: str = ""
    voice_ids: dict[str, str] | None = None
    default_voice: str = "male"
    model: str = "eleven_multilingual_v2"
    stability: float = 0.7
    similarity_boost: float = 0.75
    style: float = 0.5
    speaker_boost: bool = True
    provider: str = "elevenlabs"

    def _resolve_voice_id(self, voice: str) -> tuple[str, str]:
        aliases = self.voice_ids or {}
        requested = (voice or "").strip().lower() or self.default_voice
        if requested in {"assistant", "default"}:
            requested = self.default_voice
        if requested in aliases:
            return requested, aliases[requested]
        return requested, requested

    def synthesize(self, text: str, voice: str = "default") -> dict[str, Any]:
        requested_voice, voice_id = self._resolve_voice_id(voice)
        if not self.api_key.strip():
            return {
                "provider": self.provider,
                "voice": requested_voice,
                "audio": b"",
                "sample_rate_hz": 0,
                "format": "unknown",
                "error": "ELEVENLABS_API_KEY is required for elevenlabs TTS",
            }
        if not voice_id.strip():
            return {
                "provider": self.provider,
                "voice": requested_voice,
                "audio": b"",
                "sample_rate_hz": 0,
                "format": "unknown",
                "error": f"no voice configured for '{requested_voice}'",
            }

        body = json.dumps(
            {
                "text": text,
                "model_id": self.model,
                "optimize_streaming_latency": 4,  # Max speed for streaming
                "voice_settings": {
                    "stability": max(0.0, min(1.0, self.stability)),
                    "similarity_boost": max(0.0, min(1.0, self.similarity_boost)),
                    "style": max(0.0, min(1.0, self.style)),
                    "use_speaker_boost": bool(self.speaker_boost),
                },
            }
        ).encode("utf-8")
        req = urllib_request.Request(
            url=f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
            data=body,
            headers={
                "Accept": "audio/mpeg",
                "Content-Type": "application/json",
                "xi-api-key": self.api_key,
            },
            method="POST",
        )

        try:
            with urllib_request.urlopen(req, timeout=20.0) as response:
                audio = response.read()
                content_type = response.headers.get("Content-Type", "audio/mpeg")
        except urllib_error.HTTPError as exc:
            return {
                "provider": self.provider,
                "voice": requested_voice,
                "voice_id": voice_id,
                "audio": b"",
                "sample_rate_hz": 0,
                "format": "unknown",
                "error": f"elevenlabs request failed: http {exc.code}",
            }
        except urllib_error.URLError as exc:
            return {
                "provider": self.provider,
                "voice": requested_voice,
                "voice_id": voice_id,
                "audio": b"",
                "sample_rate_hz": 0,
                "format": "unknown",
                "error": f"elevenlabs request failed: {exc.reason}",
            }

        audio_format = "mp3" if "mpeg" in content_type else content_type
        return {
            "provider": self.provider,
            "voice": requested_voice,
            "voice_id": voice_id,
            "audio": audio,
            "sample_rate_hz": 22050,
            "format": audio_format,
            "model": self.model,
        }


def build_tts_adapter(
    provider: str,
    *,
    api_key: str = "",
    voice_ids: dict[str, str] | None = None,
    default_voice: str = "male",
    model: str = "eleven_multilingual_v2",
    fallback_provider: str = "",
    stability: float = 0.7,
    similarity_boost: float = 0.75,
    style: float = 0.5,
    speaker_boost: bool = True,
) -> TTSAdapter:
    """Construct a TTS adapter for the configured provider."""
    normalized = (provider or "").strip().lower() or "piper"
    if normalized in {"piper", "coqui"}:
        return PiperLocalTTSAdapter(
            provider=normalized,
            voice_ids=voice_ids,
            default_voice=default_voice,
        )
    if normalized == "dry_run":
        return DryRunTTSAdapter(provider=normalized)
    if normalized == "elevenlabs":
        primary = ElevenLabsTTSAdapter(
            api_key=api_key,
            voice_ids=voice_ids,
            default_voice=default_voice,
            model=model,
            stability=stability,
            similarity_boost=similarity_boost,
            style=style,
            speaker_boost=speaker_boost,
        )
        fallback_normalized = (fallback_provider or "").strip().lower()
        if fallback_normalized in {"piper", "coqui"}:
            return FallbackTTSAdapter(
                primary=primary,
                fallback=PiperLocalTTSAdapter(
                    provider=fallback_normalized,
                    voice_ids=voice_ids,
                    default_voice=default_voice,
                ),
            )
        if fallback_normalized == "dry_run":
            return FallbackTTSAdapter(
                primary=primary,
                fallback=DryRunTTSAdapter(provider=fallback_normalized),
            )
        return primary
    return UnsupportedTTSAdapter(provider=normalized)
