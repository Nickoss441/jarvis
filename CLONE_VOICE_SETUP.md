# Voice Clone Setup — Two Paths

## Status
- ✓ Audio files provided: 2 MP3 files copied to `DATASET/clone_source/`
- ✓ Voice clone script created: `scripts/clone_voice_from_audio.py`
- ✗ API Error: `"paid_plan_required"` — Your ElevenLabs subscription doesn't support instant voice cloning

Your current API key (`b0b9ed389999c...`) works for **text-to-speech synthesis** but not for **voice cloning**. Voice cloning requires a paid ElevenLabs plan.

---

## Option A: Upgrade ElevenLabs Plan (Recommended)
1. Go to [ElevenLabs Dashboard → Subscription](https://elevenlabs.io/app/subscription)
2. Upgrade to a plan that includes **Voice Cloning** (Creator or Professional)
3. After upgrade, re-run the cloning script:
   ```bash
   python scripts/clone_voice_from_audio.py --audio-dir DATASET/clone_source \
     --voice-name "Nickos Custom Clone" \
     --description "Personal cloned voice for Jarvis"
   ```
4. The script will output a new `voice_id` (e.g., `abc123def456`)
5. Update `.env` with the new voice ID:
   ```bash
   JARVIS_VOICE_TTS_VOICE_ID_MALE=abc123def456
   JARVIS_VOICE_TTS_VOICE_ID_FEMALE=abc123def456
   ```
6. Restart Jarvis server to activate the cloned voice

---

## Option B: Manual Upload via VoiceLab UI (If Available)
If your plan allows uploading via the web interface:
1. Go to [VoiceLab](https://elevenlabs.io/app/voice-lab)
2. Click **"Add Voice"** → **"Instant Voice Cloning"**
3. Upload the two audio files from `DATASET/clone_source/`:
   - `ElevenLabs_2026-04-29T05_03_58_The Asians_...mp3`
   - `ElevenLabs_2026-04-29T05_10_26_The Asians_...mp3`
4. Name it: `Nickos Custom Clone`
5. Copy the **Voice ID** from the created voice
6. Update `.env`:
   ```bash
   JARVIS_VOICE_TTS_VOICE_ID_MALE=<your_voice_id>
   JARVIS_VOICE_TTS_VOICE_ID_FEMALE=<your_voice_id>
   ```
7. Restart Jarvis server to activate

---

## Current TTS Config (Already Working)
Your current ElevenLabs setup **is working** for synthesis:
- API Key: `b0b9ed389999c...` ✓ Authenticated
- Provider: `elevenlabs` ✓
- Default Voice: `HWkBpcT0RMFmyNMInxtE` ✓
- `/hud/tts` endpoint: Working ✓
- Web Audio playback: Functional ✓

Once you complete cloning (via Option A or B), update only the `VOICE_ID_MALE` and `VOICE_ID_FEMALE` env vars — keep the API key and provider as-is.

---

## Files Involved
- Audio samples: `DATASET/clone_source/` (2 MP3 files, 882 KB total)
- Automation script: `scripts/clone_voice_from_audio.py`
- Config: `.env` (update `JARVIS_VOICE_TTS_VOICE_ID_*` after cloning)
- Server: `jarvis/approval_api.py` (no changes needed, uses env vars)

---

## Next Steps
1. **If choosing Option A**: Upgrade your plan, then run the clone script
2. **If choosing Option B**: Manually upload via VoiceLab, then update `.env`
3. After either option: Test the new voice by visiting `/hud/cc` and sending a message
