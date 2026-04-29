"""Continuous microphone voice loop for Jarvis."""
from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ...brain import Brain

logger = logging.getLogger(__name__)

_WAKE_WORD_DEFAULT = "jarvis"
_PHRASE_TIME_LIMIT = int(os.getenv("JARVIS_MIC_PHRASE_LIMIT_SECS", "10"))
_ENERGY_THRESHOLD = int(os.getenv("JARVIS_MIC_ENERGY_THRESHOLD", "300"))
_PAUSE_THRESHOLD = float(os.getenv("JARVIS_MIC_PAUSE_THRESHOLD", "0.8"))


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

                    # Strip the wake word to extract the actual command
                    command = text.lower().replace(self.wake_word, "").strip(" ,.")
                    if not command:
                        command = "yes?"

                    print(f"[voice] you  > {command}")

                    try:
                        reply = self.brain.turn(command)
                        print(f"[voice] jarvis > {reply}")
                        self._speak(reply)
                    except Exception as exc:
                        logger.error("Brain error: %s", exc)
            except KeyboardInterrupt:
                stop_event.set()
                print("\n[voice] Stopped.")
