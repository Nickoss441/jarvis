"""Vocal reply helper for the chat REPL.

Detects when the user asked Jarvis to respond vocally and speaks the reply
through a configurable speaker. The default speaker uses the built-in macOS
``say`` command so vocal output works out of the box on this deployment with
zero extra setup; on other platforms the speaker becomes a no-op rather than
crashing the REPL.
"""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from typing import Callable, Protocol


VOCAL_TRIGGER_PATTERNS: tuple[str, ...] = (
    r"\bspeak( to me| it| that)?\b",
    r"\bsay (it|that|this) (out loud|aloud|vocally)\b",
    r"\b(say|tell|read) (it|that|this) (out loud|aloud)\b",
    r"\bout loud\b",
    r"\baloud\b",
    r"\bvocal(ly)?\b",
    r"\brespond (vocally|out loud|aloud|with voice)\b",
    r"\banswer (vocally|out loud|aloud|with voice)\b",
    r"\buse your voice\b",
    r"\bvoice (reply|response|answer)\b",
)

_TRIGGER_REGEX = re.compile("|".join(VOCAL_TRIGGER_PATTERNS), re.IGNORECASE)


def wants_vocal_reply(user_input: str) -> bool:
    """Return True when the user's message asks for a spoken response."""
    if not user_input:
        return False
    return _TRIGGER_REGEX.search(user_input) is not None


class Speaker(Protocol):
    def speak(self, text: str) -> bool:
        """Speak ``text`` out loud. Return True if synthesis was attempted."""


@dataclass
class MacSaySpeaker:
    """Speak via the built-in macOS ``say`` command."""

    voice: str = ""
    rate: int = 0
    runner: Callable[[list[str]], int] | None = None

    def _binary(self) -> str | None:
        return shutil.which("say")

    def speak(self, text: str) -> bool:
        message = (text or "").strip()
        if not message:
            return False
        binary = self._binary()
        if not binary:
            return False
        argv = [binary]
        if self.voice:
            argv.extend(["-v", self.voice])
        if self.rate > 0:
            argv.extend(["-r", str(self.rate)])
        argv.append(message)
        runner = self.runner or _default_runner
        try:
            runner(argv)
        except Exception:
            return False
        return True


@dataclass
class NoopSpeaker:
    """Fallback speaker for non-macOS hosts; never raises, never speaks."""

    def speak(self, text: str) -> bool:  # noqa: ARG002 - protocol shape
        return False


def _default_runner(argv: list[str]) -> int:
    return subprocess.run(argv, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode


def build_default_speaker(voice: str = "") -> Speaker:
    """Pick the best speaker for the current platform."""
    if sys.platform == "darwin" and shutil.which("say"):
        return MacSaySpeaker(voice=voice)
    return NoopSpeaker()


__all__ = [
    "MacSaySpeaker",
    "NoopSpeaker",
    "Speaker",
    "VOCAL_TRIGGER_PATTERNS",
    "build_default_speaker",
    "wants_vocal_reply",
]
