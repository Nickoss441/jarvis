from jarvis.perception.voice import (
    WakeWordListener,
    build_stt_adapter,
    build_tts_adapter,
    build_voice_adapter_stack,
    build_wake_word_adapter,
)
from jarvis.perception.voice.mic import (
    extract_voice_command,
    parse_spotify_voice_command,
    spotify_voice_reply,
)


class _FakeResponse:
    def __init__(self, payload: bytes, content_type: str = "audio/mpeg") -> None:
        self._payload = payload
        self.headers = {"Content-Type": content_type}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self) -> bytes:
        return self._payload


def test_wake_word_dry_run_detects_case_insensitive_match():
    adapter = build_wake_word_adapter(provider="dry_run", wake_word="Jarvis")

    assert adapter.detect_trigger(b"hello jarvis") is True
    assert adapter.detect_trigger(b"HELLO JARVIS") is True


def test_wake_word_returns_false_when_absent():
    adapter = build_wake_word_adapter(provider="dry_run", wake_word="jarvis")

    assert adapter.detect_trigger(b"hello friday") is False


def test_wake_word_unknown_provider_uses_unsupported_adapter():
    adapter = build_wake_word_adapter(provider="unknown", wake_word="jarvis")

    assert adapter.detect_trigger(b"jarvis") is False


def test_stt_dry_run_returns_text_payload():
    adapter = build_stt_adapter("faster-whisper")

    out = adapter.transcribe(b"hello world", language="en")

    assert out["provider"] == "faster-whisper"
    assert out["text"] == "hello world"
    assert out["confidence"] == 1.0


def test_stt_dry_run_uses_default_when_empty_input():
    adapter = build_stt_adapter("dry_run")

    out = adapter.transcribe(b"")

    assert out["text"] == "[dry_run transcript]"


def test_stt_unknown_provider_returns_error_payload():
    adapter = build_stt_adapter("custom-cloud")

    out = adapter.transcribe(b"voice")

    assert "error" in out
    assert out["text"] == ""


def test_tts_dry_run_synthesizes_audio_bytes():
    adapter = build_tts_adapter("piper")

    out = adapter.synthesize("hello", voice="assistant")

    assert out["provider"] == "piper"
    assert out["voice"] == "assistant"
    assert out["audio"] == b"hello"
    assert out["sample_rate_hz"] == 16000


def test_tts_unknown_provider_returns_error_payload():
    adapter = build_tts_adapter("vendor-x")

    out = adapter.synthesize("hello")

    assert "error" in out
    assert out["audio"] == b""


def test_tts_elevenlabs_without_api_key_returns_error_payload():
    adapter = build_tts_adapter(
        "elevenlabs",
        voice_ids={"male": "voice-m", "female": "voice-f"},
        default_voice="male",
    )

    out = adapter.synthesize("hello", voice="male")

    assert "error" in out
    assert out["audio"] == b""


def test_tts_elevenlabs_uses_selected_voice_id(monkeypatch):
    captured = {}

    def _fake_urlopen(request_obj, timeout=0):
        captured["url"] = request_obj.full_url
        captured["api_key"] = request_obj.headers.get("Xi-api-key")
        captured["timeout"] = timeout
        return _FakeResponse(b"mp3-data")

    monkeypatch.setattr("jarvis.perception.voice.tts.urllib_request.urlopen", _fake_urlopen)

    adapter = build_tts_adapter(
        "elevenlabs",
        api_key="key-123",
        voice_ids={"male": "voice-m", "female": "voice-f"},
        default_voice="female",
    )

    out = adapter.synthesize("hello", voice="female")

    assert out["provider"] == "elevenlabs"
    assert out["voice"] == "female"
    assert out["voice_id"] == "voice-f"
    assert out["audio"] == b"mp3-data"
    assert captured["url"].endswith("/voice-f")


def test_tts_elevenlabs_can_fallback_to_local_voice_on_error():
    adapter = build_tts_adapter(
        "elevenlabs",
        voice_ids={"male": "voice-m", "female": "voice-f"},
        default_voice="male",
        fallback_provider="piper",
    )

    out = adapter.synthesize("hello", voice="male")

    assert out["provider"] == "piper"
    assert out["audio"] == b"hello"
    assert out["fallback_from"] == "elevenlabs"
    assert "ELEVENLABS_API_KEY" in out["fallback_reason"]


def test_build_voice_adapter_stack_wires_adapters():
    stack = build_voice_adapter_stack(
        wake_word="jarvis",
        stt_provider="whisperx",
        tts_provider="coqui",
    )

    assert stack.wake_word.detect_trigger(b"jarvis wake up") is True
    stt_out = stack.stt.transcribe(b"transcript")
    tts_out = stack.tts.synthesize("reply")

    assert stt_out["provider"] == "whisperx"
    assert tts_out["provider"] == "coqui"


def test_build_voice_adapter_stack_wires_elevenlabs_tts(monkeypatch):
    monkeypatch.setattr(
        "jarvis.perception.voice.tts.urllib_request.urlopen",
        lambda request_obj, timeout=0: _FakeResponse(b"voice-bytes"),
    )

    stack = build_voice_adapter_stack(
        wake_word="jarvis",
        stt_provider="faster-whisper",
        tts_provider="elevenlabs",
        tts_api_key="key-123",
        tts_voice_ids={"male": "voice-m", "female": "voice-f"},
        tts_default_voice="male",
    )

    tts_out = stack.tts.synthesize("reply", voice="male")

    assert tts_out["provider"] == "elevenlabs"
    assert tts_out["voice_id"] == "voice-m"


def test_wake_word_listener_tracks_chunks_and_triggers() -> None:
    adapter = build_wake_word_adapter(provider="dry_run", wake_word="jarvis")
    listener = WakeWordListener(adapter=adapter)

    out1 = listener.ingest(b"hello there")
    out2 = listener.ingest(b"jarvis wake up")

    assert out1["triggered"] is False
    assert out1["chunks_seen"] == 1
    assert out1["triggers"] == 0
    assert out2["triggered"] is True
    assert out2["chunks_seen"] == 2
    assert out2["triggers"] == 1


def test_extract_voice_command_removes_wake_word_and_prefix() -> None:
    command = extract_voice_command("hey jarvis play blinding lights on spotify", "jarvis")
    assert command == "play blinding lights on spotify"


def test_parse_spotify_voice_command_maps_play_phrase() -> None:
    args = parse_spotify_voice_command("can you play blinding lights on spotify")
    assert args == {"action": "play", "query": "blinding lights"}


def test_parse_spotify_voice_command_maps_pause_phrase() -> None:
    args = parse_spotify_voice_command("pause spotify")
    assert args == {"action": "pause"}


def test_spotify_voice_reply_formats_playback_confirmation() -> None:
    reply = spotify_voice_reply(
        {
            "ok": True,
            "action": "play",
            "track": "Blinding Lights",
            "artist": "The Weeknd",
        },
        {"action": "play", "query": "blinding lights"},
    )
    assert reply == "Playing Blinding Lights by The Weeknd on Spotify."
