#!/usr/bin/env python3
"""Generate an overnight TTS dataset for voice cloning prep.

This script repeatedly sends prompt lines to ElevenLabs TTS and saves
MP3 files + JSONL metadata so you can build a large dataset overnight.

Usage examples:
    python scripts/overnight_tts_dataset.py --hours 8
    python scripts/overnight_tts_dataset.py --hours 10 --shuffle --pause 1.2
    python scripts/overnight_tts_dataset.py --prompt-file docs/voice_prompts.txt
"""

from __future__ import annotations

import argparse
import json
import os
import random
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_PROMPTS = [
    "Hello, I am ready.",
    "Good morning. Here is your schedule.",
    "The outside temperature is twelve degrees Celsius.",
    "Light rain is expected in twenty minutes.",
    "Wind speed is twenty kilometers per hour from the west.",
    "Traffic is currently moderate on your usual route.",
    "Estimated travel time to the office is twenty three minutes.",
    "There is congestion on the ring road. I recommend an alternate route.",
    "Your next meeting starts at nine thirty.",
    "I drafted the reply and saved it for approval.",
    "The fastest route is shorter by six minutes.",
    "Rain intensity will increase after five o'clock.",
    "You should leave in twelve minutes to arrive on time.",
    "I can call ahead if you want me to confirm the reservation.",
    "I found a delay on the train line into the city.",
    "Indoor humidity is currently forty eight percent.",
    "The package is scheduled to arrive before noon.",
    "I paused the trade request because the policy limit was reached.",
    "I am waiting for your approval before sending the message.",
    "Today is Friday, April twenty sixth, twenty twenty six.",
    "The address is one hundred twenty three Market Street.",
    "Turn left in two hundred meters.",
    "Continue straight for one point five kilometers.",
    "Arrival time is seven fourteen p.m.",
    "The total cost is forty two euros and fifty cents.",
    "Call John when you arrive.",
    "Message Sarah that you are running five minutes late.",
    "The battery is at sixty four percent.",
    "Latitude fifty two point three six seven. Longitude four point nine zero four.",
]


def load_env_file(path: Path) -> None:
    """Load simple KEY=VALUE pairs from .env into process env if absent."""
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def load_prompts(path: Path | None) -> list[str]:
    if path is None:
        return list(DEFAULT_PROMPTS)
    if not path.exists():
        raise FileNotFoundError(f"Prompt file not found: {path}")
    lines: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        lines.append(line)
    if not lines:
        raise ValueError(f"Prompt file has no usable lines: {path}")
    return lines


def elevenlabs_tts(api_key: str, voice_id: str, model_id: str, text: str, timeout: float) -> bytes:
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    payload = {
        "text": text,
        "model_id": model_id,
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
            "xi-api-key": api_key,
            "User-Agent": "jarvis-overnight-tts/1.0",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 - fixed trusted API
        return resp.read()


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    load_env_file(repo_root / ".env")

    parser = argparse.ArgumentParser(description="Generate an overnight ElevenLabs TTS dataset")
    parser.add_argument("--hours", type=float, default=8.0, help="How long to run (hours)")
    parser.add_argument("--pause", type=float, default=0.8, help="Seconds between requests")
    parser.add_argument("--timeout", type=float, default=30.0, help="HTTP timeout seconds")
    parser.add_argument("--shuffle", action="store_true", help="Shuffle prompts each cycle")
    parser.add_argument("--max-files", type=int, default=0, help="Optional hard cap (0 = no cap)")
    parser.add_argument("--model", default=os.getenv("JARVIS_VOICE_TTS_MODEL", "eleven_multilingual_v2"))
    parser.add_argument("--voice-id", default=os.getenv("JARVIS_VOICE_TTS_VOICE_ID_MALE", ""))
    parser.add_argument("--api-key", default=os.getenv("ELEVENLABS_API_KEY", ""))
    parser.add_argument("--prompt-file", type=Path, default=None, help="Text file: one prompt per line")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("DATASET") / "overnight_tts_clone_seed",
        help="Directory for generated mp3 files and metadata",
    )
    args = parser.parse_args()

    api_key = args.api_key.strip()
    voice_id = args.voice_id.strip()

    if not api_key:
        print("ERROR: Missing ElevenLabs API key. Set ELEVENLABS_API_KEY or pass --api-key.")
        return 1
    if not voice_id:
        print("ERROR: Missing voice id. Set JARVIS_VOICE_TTS_VOICE_ID_MALE or pass --voice-id.")
        return 1
    if args.hours <= 0:
        print("ERROR: --hours must be > 0")
        return 1
    if args.pause < 0:
        print("ERROR: --pause must be >= 0")
        return 1

    prompts = load_prompts(args.prompt_file)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    metadata_path = args.output_dir / "metadata.jsonl"

    end_ts = time.time() + (args.hours * 3600)
    sequence = 0
    errors = 0

    print("=" * 72)
    print("Overnight TTS dataset generation started")
    print(f"Output dir : {args.output_dir}")
    print(f"Voice ID   : {voice_id}")
    print(f"Model      : {args.model}")
    print(f"Prompts    : {len(prompts)}")
    print(f"Runtime    : {args.hours:.2f} hour(s)")
    print("=" * 72)

    while time.time() < end_ts:
        cycle = list(prompts)
        if args.shuffle:
            random.shuffle(cycle)

        for prompt in cycle:
            if time.time() >= end_ts:
                break
            if args.max_files > 0 and sequence >= args.max_files:
                break

            sequence += 1
            stem = f"tts_{sequence:06d}"
            audio_path = args.output_dir / f"{stem}.mp3"

            try:
                audio = elevenlabs_tts(api_key, voice_id, args.model, prompt, args.timeout)
                audio_path.write_bytes(audio)
                row = {
                    "id": stem,
                    "timestamp_utc": utc_now(),
                    "text": prompt,
                    "bytes": len(audio),
                    "voice_id": voice_id,
                    "model": args.model,
                    "path": str(audio_path).replace("\\", "/"),
                }
                with metadata_path.open("a", encoding="utf-8") as fh:
                    fh.write(json.dumps(row, ensure_ascii=True) + "\n")
                print(f"[{sequence:06d}] ok {len(audio)} bytes")
            except urllib.error.HTTPError as exc:
                errors += 1
                body = exc.read().decode("utf-8", errors="replace") if hasattr(exc, "read") else ""
                print(f"[{sequence:06d}] HTTP {exc.code}: {body[:220]}")
            except Exception as exc:  # noqa: BLE001
                errors += 1
                print(f"[{sequence:06d}] ERROR: {exc}")

            if args.pause > 0:
                time.sleep(args.pause)

        if args.max_files > 0 and sequence >= args.max_files:
            break

    print("=" * 72)
    print("Overnight TTS dataset generation finished")
    print(f"Files attempted : {sequence}")
    print(f"Errors          : {errors}")
    print(f"Metadata        : {metadata_path}")
    print("=" * 72)

    return 0 if sequence > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
