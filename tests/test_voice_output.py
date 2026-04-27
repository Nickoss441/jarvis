"""Tests for the vocal reply helper."""
from __future__ import annotations

import pytest

from jarvis import voice_output
from jarvis.voice_output import (
    MacSaySpeaker,
    NoopSpeaker,
    build_default_speaker,
    wants_vocal_reply,
)


@pytest.mark.parametrize(
    "user_input",
    [
        "say it out loud",
        "Please respond vocally.",
        "Read that aloud for me",
        "Use your voice and tell me",
        "give me a voice reply",
        "speak it",
        "answer out loud please",
    ],
)
def test_wants_vocal_reply_detects_triggers(user_input: str) -> None:
    assert wants_vocal_reply(user_input) is True


@pytest.mark.parametrize(
    "user_input",
    [
        "",
        "what is the weather",
        "draft an email",
        "say hello to mom",  # plain "say" without trigger phrases
        "tell me about saturn",
    ],
)
def test_wants_vocal_reply_ignores_plain_messages(user_input: str) -> None:
    assert wants_vocal_reply(user_input) is False


def test_mac_say_speaker_runs_say_with_text() -> None:
    captured: list[list[str]] = []

    def runner(argv: list[str]) -> int:
        captured.append(argv)
        return 0

    speaker = MacSaySpeaker(runner=runner)
    if not speaker._binary():
        pytest.skip("`say` binary not available on this host")

    assert speaker.speak("hello there") is True
    assert captured, "speaker did not invoke runner"
    argv = captured[0]
    assert argv[-1] == "hello there"
    assert argv[0].endswith("say")


def test_mac_say_speaker_skips_empty_text() -> None:
    captured: list[list[str]] = []

    def runner(argv: list[str]) -> int:
        captured.append(argv)
        return 0

    speaker = MacSaySpeaker(runner=runner)
    assert speaker.speak("   ") is False
    assert captured == []


def test_mac_say_speaker_swallows_runner_errors() -> None:
    def runner(argv: list[str]) -> int:  # noqa: ARG001
        raise OSError("simulated failure")

    speaker = MacSaySpeaker(runner=runner)
    if not speaker._binary():
        pytest.skip("`say` binary not available on this host")
    assert speaker.speak("hello") is False


def test_noop_speaker_never_speaks() -> None:
    assert NoopSpeaker().speak("hello") is False


def test_build_default_speaker_returns_a_speaker(monkeypatch: pytest.MonkeyPatch) -> None:
    speaker = build_default_speaker()
    assert hasattr(speaker, "speak")


def test_build_default_speaker_falls_back_when_no_say(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(voice_output.shutil, "which", lambda _name: None)
    speaker = build_default_speaker()
    assert isinstance(speaker, NoopSpeaker)
