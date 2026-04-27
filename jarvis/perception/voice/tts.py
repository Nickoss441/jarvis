"""Text-to-speech adapter scaffold for phase-2 voice perception."""
from __future__ import annotations

from dataclasses import dataclass
import json
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
) -> TTSAdapter:
    """Construct a TTS adapter for the configured provider."""
    normalized = (provider or "").strip().lower() or "piper"
    if normalized in {"piper", "dry_run", "coqui"}:
        return DryRunTTSAdapter(provider=normalized)
    if normalized == "elevenlabs":
        primary = ElevenLabsTTSAdapter(
            api_key=api_key,
            voice_ids=voice_ids,
            default_voice=default_voice,
            model=model,
        )
        fallback_normalized = (fallback_provider or "").strip().lower()
        if fallback_normalized in {"piper", "dry_run", "coqui"}:
            return FallbackTTSAdapter(
                primary=primary,
                fallback=DryRunTTSAdapter(provider=fallback_normalized),
            )
        return primary
    return UnsupportedTTSAdapter(provider=normalized)
