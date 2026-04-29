#!/usr/bin/env python3
"""Upload audio files to ElevenLabs and create an instant voice clone.

This script uploads multiple audio files and creates a cloned voice in ElevenLabs
that can then be used in Jarvis for TTS synthesis.

Usage:
    python scripts/clone_voice_from_audio.py --audio-dir DATASET/overnight_tts_clone_seed
    python scripts/clone_voice_from_audio.py --audio-file sample.mp3 --voice-name "My Clone"
    python scripts/clone_voice_from_audio.py --audio-dir recordings/ --voice-name "Custom Voice"
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
from pathlib import Path


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


def create_voice_clone(
    api_key: str,
    voice_name: str,
    audio_files: list[Path],
    description: str = "",
    labels: str = "",
) -> dict:
    """Create an instant voice clone from audio files via ElevenLabs API.
    
    Uses the `/voices/add` endpoint with multipart form-data.
    """
    try:
        import httpx
    except ImportError:
        print("ERROR: httpx not installed. Run: pip install httpx")
        raise
    
    url = "https://api.elevenlabs.io/v1/voices/add"
    
    # Build form data dict for multipart encoding
    files = []
    data = {"name": voice_name}
    
    if description:
        data["description"] = description
    else:
        data["description"] = "Cloned voice via Jarvis automation"
    
    if labels:
        data["labels"] = labels
    else:
        data["labels"] = "clone,custom"
    
    # Add audio files to multipart
    for audio_path in audio_files:
        audio_bytes = audio_path.read_bytes()
        files.append(("files", (audio_path.name, audio_bytes, "audio/mpeg")))
    
    with httpx.Client() as client:
        resp = client.post(
            url,
            data=data,
            files=files,
            headers={"xi-api-key": api_key},
            timeout=120,
        )
        
        if resp.status_code >= 400:
            try:
                error_detail = resp.json()
                error_msg = str(error_detail)
            except (json.JSONDecodeError, ValueError):
                error_msg = resp.text[:500]
            
            # Check for specific paid plan error
            if "paid_plan_required" in error_msg or "instant_voice_cloning" in error_msg:
                raise ValueError(
                    "PAID_PLAN: Your ElevenLabs subscription doesn't support instant voice cloning. "
                    "Upgrade at: https://elevenlabs.io/app/subscription"
                )
            else:
                raise ValueError(f"API error ({resp.status_code}): {error_msg}")
        
        return resp.json()


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    load_env_file(repo_root / ".env")
    
    parser = argparse.ArgumentParser(
        description="Create an ElevenLabs instant voice clone from audio files"
    )
    parser.add_argument(
        "--audio-file",
        type=Path,
        help="Single MP3 file to clone from",
    )
    parser.add_argument(
        "--audio-dir",
        type=Path,
        help="Directory with MP3 files to combine for clone",
    )
    parser.add_argument(
        "--voice-name",
        default="Jarvis Clone",
        help="Display name for the cloned voice",
    )
    parser.add_argument(
        "--description",
        default="Custom cloned voice created via Jarvis automation",
        help="Voice description for ElevenLabs",
    )
    parser.add_argument(
        "--labels",
        default="clone,custom",
        help="Comma-separated labels for voice organization",
    )
    parser.add_argument(
        "--api-key",
        default=os.getenv("ELEVENLABS_API_KEY", ""),
        help="ElevenLabs API key",
    )
    
    args = parser.parse_args()
    
    api_key = args.api_key.strip()
    if not api_key:
        print("ERROR: Missing ElevenLabs API key. Set ELEVENLABS_API_KEY or pass --api-key.")
        return 1
    
    # Collect audio files
    audio_files: list[Path] = []
    if args.audio_file:
        audio_files = [args.audio_file]
    elif args.audio_dir:
        audio_files = sorted(args.audio_dir.glob("*.mp3"))
    else:
        print("ERROR: Provide --audio-file or --audio-dir")
        return 1
    
    audio_files = [f for f in audio_files if f.is_file()]
    if not audio_files:
        print(f"ERROR: No MP3 files found in {args.audio_dir or args.audio_file}")
        return 1
    
    print("=" * 72)
    print("ElevenLabs Instant Voice Clone Creation")
    print("=" * 72)
    print(f"Voice name   : {args.voice_name}")
    print(f"Description  : {args.description}")
    print(f"Labels       : {args.labels}")
    print(f"Audio files  : {len(audio_files)}")
    for af in audio_files[:5]:
        print(f"  - {af.name}")
    if len(audio_files) > 5:
        print(f"  ... and {len(audio_files) - 5} more")
    print("=" * 72)
    
    try:
        result = create_voice_clone(
            api_key=api_key,
            voice_name=args.voice_name,
            audio_files=audio_files,
            description=args.description,
            labels=args.labels,
        )
        
        voice_id = result.get("voice_id", "")
        if not voice_id:
            print("ERROR: No voice_id in response")
            print(json.dumps(result, indent=2))
            return 1
        
        print("\n" + "=" * 72)
        print("VOICE CLONE CREATED SUCCESSFULLY")
        print("=" * 72)
        print(f"Voice ID  : {voice_id}")
        print(f"Name      : {result.get('name', 'N/A')}")
        print(f"Sharing   : {result.get('sharing', {}).get('status', 'N/A')}")
        print("\nTo use this voice in Jarvis, add to .env:")
        print(f"  JARVIS_VOICE_TTS_VOICE_ID_MALE={voice_id}")
        print(f"  JARVIS_VOICE_TTS_VOICE_ID_FEMALE={voice_id}")
        print("\nThen restart the Jarvis server.")
        print("=" * 72)
        
        return 0
    except Exception as exc:  # noqa: BLE001
        error_text = str(exc)
        
        # Check for paid plan requirement
        if "PAID_PLAN:" in error_text or "paid_plan_required" in error_text:
            print("\n" + "=" * 72)
            print("PLAN UPGRADE REQUIRED")
            print("=" * 72)
            print("Your ElevenLabs subscription does NOT include instant voice cloning.")
            print("\nTo use voice cloning, you must:")
            print("  1. Go to https://elevenlabs.io/app/subscription")
            print("  2. Upgrade to Creator or Professional plan")
            print("  3. After upgrade, run this script again")
            print("\nAlternatively, use VoiceLab UI for manual upload:")
            print("  https://elevenlabs.io/app/voice-lab → Add Voice → Instant Voice Cloning")
            print("=" * 72)
            return 1
        
        print(f"\nERROR: {type(exc).__name__}: {exc}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
