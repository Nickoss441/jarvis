"""Continuous microphone voice loop for Jarvis."""
from __future__ import annotations

import logging
import os
import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ...brain import Brain

logger = logging.getLogger(__name__)

_WAKE_WORD_DEFAULT = "jarvis"
_PHRASE_TIME_LIMIT = int(os.getenv("JARVIS_MIC_PHRASE_LIMIT_SECS", "10"))
_ENERGY_THRESHOLD = int(os.getenv("JARVIS_MIC_ENERGY_THRESHOLD", "300"))
_PAUSE_THRESHOLD = float(os.getenv("JARVIS_MIC_PAUSE_THRESHOLD", "0.8"))


def extract_voice_command(transcript: str, wake_word: str) -> str:
    """Extract the user command from transcript text containing the wake word."""
    text = (transcript or "").strip().lower()
    wake = (wake_word or "").strip().lower()
    if not text or not wake:
        return ""

    idx = text.find(wake)
    if idx < 0:
        return ""

    # Remove wake-word occurrence while keeping surrounding phrase text.
    command = f"{text[:idx]} {text[idx + len(wake):]}".strip(" ,.!?\t\n")

    # Trim common preamble fillers left by natural speech.
    for prefix in ("hey ", "ok ", "okay "):
        if command.startswith(prefix):
            command = command[len(prefix):].lstrip()
            break

    return " ".join(command.split())


def parse_spotify_voice_command(command: str) -> dict[str, Any] | None:
    """Parse natural voice phrases into spotify tool arguments when obvious."""
    raw = " ".join((command or "").strip().lower().split())
    if not raw or "spotify" not in raw:
        return None

    normalized = re.sub(
        r"^(hey|ok|okay|please|can you|could you|would you|will you)\s+",
        "",
        raw,
    )

    action = ""
    query = ""

    if (
        "liked songs" in normalized
        or "my liked" in normalized
        or "liked tracks" in normalized
        or "favorites" in normalized
        or "favourites" in normalized
    ):
        action = "liked"

    if not action and (" play " in f" {normalized} " or normalized.startswith("play ")):
        action = "play"
        play_idx = normalized.find("play")
        query = normalized[play_idx + len("play"):].strip(" ,.!?")
        if query.startswith("me "):
            query = query[3:].lstrip()
        for suffix in (
            " on spotify",
            " in spotify",
            " at spotify",
            " from spotify",
            " and spotify",
            " spotify",
        ):
            if query.endswith(suffix):
                query = query[: -len(suffix)].rstrip(" ,.!?")
                break
    elif "pause" in normalized:
        action = "pause"
    elif "skip" in normalized or "next track" in normalized or "next song" in normalized:
        action = "skip"
    elif "previous" in normalized or "back" in normalized:
        action = "previous"
    elif "what is playing" in normalized or "what's playing" in normalized or "currently playing" in normalized:
        action = "current"

    if not action:
        return None

    if action == "play" and query:
        return {"action": "play", "query": query}
    return {"action": action}


def spotify_voice_reply(result: dict[str, Any], args: dict[str, Any]) -> str:
    """Build a concise spoken response from spotify tool output."""
    if not isinstance(result, dict):
        return "Spotify command returned an invalid response."
    if not result.get("ok"):
        return f"Spotify failed: {result.get('error', 'unknown error')}"

    action = str(result.get("action") or args.get("action") or "").lower()
    if action == "play":
        track = str(result.get("track") or "").strip()
        artist = str(result.get("artist") or "").strip()
        if track and artist:
            return f"Playing {track} by {artist} on Spotify."
        if track:
            return f"Playing {track} on Spotify."
        return "Resumed Spotify playback."
    if action == "pause":
        return "Paused Spotify."
    if action == "skip":
        return "Skipped to the next track."
    if action == "previous":
        return "Went back to the previous track."
    if action == "current":
        if result.get("playing") and result.get("track"):
            artist = str(result.get("artist") or "").strip()
            if artist:
                return f"Now playing {result['track']} by {artist}."
            return f"Now playing {result['track']}."
        return "Nothing is currently playing on Spotify."
    if action == "liked":
        count = int(result.get("count") or 0)
        track = str(result.get("track") or "").strip()
        artist = str(result.get("artist") or "").strip()
        if track and artist:
            return f"Playing your liked songs on Spotify, starting with {track} by {artist}."
        if track:
            return f"Playing your liked songs on Spotify, starting with {track}."
        if count > 0:
            return f"Playing your liked songs on Spotify. Queued {count} tracks."
        return "Playing your liked songs on Spotify."
    return "Spotify command completed."


class MicVoiceLoop:
    """
    Capture mic audio, detect wake word via Whisper transcript, route command
    to Brain, and speak the reply via the TTS adapter.

    Audio pipeline:
        sounddevice/pyaudio (via SpeechRecognition VAD)
        → raw PCM s16le 16 kHz bytes
        → FasterWhisperSTTAdapter
        → wake word check
        → Brain.turn()
        → TTS adapter + sounddevice playback
    """

    def __init__(
        self,
        brain: Brain,
        wake_word: str = _WAKE_WORD_DEFAULT,
        tts_adapter: Any | None = None,
        whisper_model_size: str = "base",
    ) -> None:
        self.brain = brain
        self.wake_word = wake_word.lower().strip()
        self.tts = tts_adapter
        self.whisper_model_size = whisper_model_size
        self._whisper_model: Any = None

    # ── Whisper ──────────────────────────────────────────────────────────────

    def _load_whisper(self) -> Any:
        if self._whisper_model is None:
            from faster_whisper import WhisperModel
            print(
                f"[voice] Loading Whisper '{self.whisper_model_size}' model "
                "(first run downloads ~150 MB)..."
            )
            self._whisper_model = WhisperModel(
                self.whisper_model_size, device="cpu", compute_type="int8"
            )
            print("[voice] Whisper ready.")
        return self._whisper_model

    def _transcribe_audio(self, audio: Any) -> str:
        """Transcribe a speech_recognition AudioData object to text."""
        import numpy as np
        model = self._load_whisper()
        raw = audio.get_raw_data(convert_rate=16000, convert_width=2)
        audio_np = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
        segments, _ = model.transcribe(audio_np, beam_size=5, language="en")
        return " ".join(seg.text for seg in segments).strip()

    # ── TTS playback ─────────────────────────────────────────────────────────

    def _speak(self, text: str) -> None:
        if not self.tts:
            return
        result = self.tts.synthesize(text)
        if result.get("error") or not result.get("audio"):
            logger.warning("TTS skipped: %s", result.get("error", "no audio"))
            return
        try:
            import numpy as np
            import sounddevice as sd
            audio_np = np.frombuffer(result["audio"], dtype=np.int16)
            sd.play(audio_np, samplerate=result["sample_rate_hz"], blocking=True)
        except Exception as exc:
            logger.warning("TTS playback failed: %s", exc)

    # ── Main loop ─────────────────────────────────────────────────────────────

    def run(self) -> None:
        import threading
        import speech_recognition as sr

        recognizer = sr.Recognizer()
        recognizer.energy_threshold = _ENERGY_THRESHOLD
        recognizer.dynamic_energy_threshold = True
        recognizer.pause_threshold = _PAUSE_THRESHOLD

        print(f'[voice] Say "{self.wake_word}" to wake me up. Ctrl+C to stop.')

        with sr.Microphone() as source:
            print("[voice] Calibrating for ambient noise (3 s)...")
            recognizer.adjust_for_ambient_noise(source, duration=3)
            print(f"[voice] Energy threshold set to {recognizer.energy_threshold:.0f}. Listening...")

            # Background thread: recalibrate every 30 s so it adapts to room changes
            stop_event = threading.Event()

            def _recalibrate() -> None:
                while not stop_event.wait(30):
                    try:
                        with sr.Microphone() as recal_src:
                            recognizer.adjust_for_ambient_noise(recal_src, duration=1)
                            logger.debug(
                                "Recalibrated energy threshold to %.0f",
                                recognizer.energy_threshold,
                            )
                    except Exception:
                        pass

            threading.Thread(target=_recalibrate, daemon=True).start()

            try:
                while True:
                    try:
                        audio = recognizer.listen(
                            source, timeout=None, phrase_time_limit=_PHRASE_TIME_LIMIT
                        )
                    except sr.WaitTimeoutError:
                        continue

                    try:
                        text = self._transcribe_audio(audio)
                    except Exception as exc:
                        logger.warning("Transcription error: %s", exc)
                        continue

                    if not text:
                        continue

                    logger.debug("heard: %s", text)

                    if self.wake_word not in text.lower():
                        continue

                    command = extract_voice_command(text, self.wake_word)
                    if not command:
                        command = "yes?"

                    print(f"[voice] you  > {command}")

                    try:
                        spotify_args = parse_spotify_voice_command(command)
                        if spotify_args:
                            result = self.brain._dispatch("spotify", spotify_args)
                            reply = spotify_voice_reply(result, spotify_args)
                        else:
                            reply = self.brain.turn(command)
                        print(f"[voice] jarvis > {reply}")
                        self._speak(reply)
                    except Exception as exc:
                        logger.error("Brain error: %s", exc)
            except KeyboardInterrupt:
                stop_event.set()
                print("\n[voice] Stopped.")
