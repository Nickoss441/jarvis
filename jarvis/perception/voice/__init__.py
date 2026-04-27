"""Voice perception scaffold (wake-word, STT, TTS adapters)."""
from __future__ import annotations

from dataclasses import dataclass

from .stt import STTAdapter, build_stt_adapter
from .tts import TTSAdapter, build_tts_adapter
from .wake_word import WakeWordAdapter, build_wake_word_adapter


@dataclass
class VoiceAdapterStack:
    """Container for configured voice adapters."""

    wake_word: WakeWordAdapter
    stt: STTAdapter
    tts: TTSAdapter


def build_voice_adapter_stack(
    wake_word: str,
    stt_provider: str,
    tts_provider: str,
    *,
    tts_api_key: str = "",
    tts_voice_ids: dict[str, str] | None = None,
    tts_default_voice: str = "male",
    tts_model: str = "eleven_multilingual_v2",
    tts_fallback_provider: str = "",
) -> VoiceAdapterStack:
    """Build the phase-2 voice adapter stack from provider names."""
    return VoiceAdapterStack(
        wake_word=build_wake_word_adapter(provider="local", wake_word=wake_word),
        stt=build_stt_adapter(stt_provider),
        tts=build_tts_adapter(
            tts_provider,
            api_key=tts_api_key,
            voice_ids=tts_voice_ids,
            default_voice=tts_default_voice,
            model=tts_model,
            fallback_provider=tts_fallback_provider,
        ),
    )


__all__ = [
    "WakeWordAdapter",
    "STTAdapter",
    "TTSAdapter",
    "VoiceAdapterStack",
    "build_wake_word_adapter",
    "build_stt_adapter",
    "build_tts_adapter",
    "build_voice_adapter_stack",
]
