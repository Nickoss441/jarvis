# Voice Output & Vocal Reply Triggers

**Last Updated**: 2026-04-30  
**Status**: Implementation in progress (pattern recognition complete)

## Overview

Jarvis supports **vocal reply triggers** — special voice commands that instruct the system to respond with spoken audio. When you use the phrase `respond vocally: <command>`, Jarvis executes the command and speaks the response aloud using the configured TTS provider.

## Recognized Vocal Trigger Phrases

### Primary Trigger: "respond vocally: X"

**Pattern**: `respond vocally: <command>`  
**Examples**:
- "respond vocally: status report" → Speaks the current system status
- "respond vocally: what is the weather" → Speaks weather information
- "respond vocally: read my latest email" → Speaks email summary
- "respond vocally: what is bitcoin price" → Speaks current BTC price

**Case-Insensitive**: Yes  
**With Continuation**: `respond vocally: status report and show the dashboard` (only "status report" is captured; "and show the dashboard" is ignored)

## How It Works

### 1. Voice Input (STT)
```
User speaks: "respond vocally: status report"
       ↓
STT (faster-whisper) transcribes to text
       ↓
Text: "respond vocally: status report"
```

### 2. Trigger Recognition
```
Voice text → parse_voice_command()
       ↓
Pattern matched: respond vocally: status report
       ↓
VoiceCommand(
    trigger_type="respond_vocally",
    payload="status report",
    raw_text="respond vocally: status report"
)
```

### 3. Command Execution
```
payload="status report"
       ↓
Query agent brain: "status report"
       ↓
Response: "System healthy. 3 pending approvals. 1 trade active. Audio: online."
```

### 4. Vocal Response (TTS)
```
Response text
       ↓
TTS Provider (piper / elevenlabs / openai)
       ↓
Audio playback (speaker output)
```

## Implementation Details

### Module: `jarvis/voice_trigger.py`

**Main Functions**:

```python
def parse_voice_command(text: str) -> Optional[VoiceCommand]:
    """Parse voice input for trigger patterns.
    
    Returns VoiceCommand if recognized trigger found, None otherwise.
    """

def should_respond_vocally(command: VoiceCommand) -> bool:
    """Check if command requires vocal response."""

def extract_vocal_payload(command: VoiceCommand) -> str:
    """Extract the actual command to execute."""
```

**Data Structure**:

```python
@dataclass
class VoiceCommand:
    trigger_type: str  # "respond_vocally", "interrupt", "wake", etc.
    payload: str       # The command to execute
    raw_text: str      # Original voice transcript
```

### Smoke Test: `scripts/smoke_test_vocal_agent.py`

Validates:
1. ✓ Voice command parsing (pattern recognition)
2. ✓ Agent dialogue routing (`/hud/ask` endpoint)
3. ✓ Approval system integration
4. ~ Vocal response generation (TTS integration pending)

**Run**: 
```bash
python scripts/smoke_test_vocal_agent.py
```

### Unit Tests: `tests/test_voice_trigger.py`

Coverage:
- ✓ Basic pattern matching
- ✓ Case-insensitive matching
- ✓ Whitespace handling
- ✓ Multi-word commands
- ✓ Empty/None text handling
- ✓ Integration workflow

**Run**:
```bash
python -m pytest tests/test_voice_trigger.py -v
```

## Configuration

### Voice Stack

Set via `jarvis/config.py`:

```python
voice_stack: str = "local"              # local, elevenlabs, openai
voice_tts_provider: str = "piper"       # piper, elevenlabs, openai
voice_tts_model: str = "eleven_multilingual_v2"
voice_tts_persona: str = "jarvis"       # jarvis, eva, etc.
voice_stt_provider: str = "faster-whisper"  # faster-whisper, openai, local
```

### Environment Variables

```bash
# STT/TTS API keys
export JARVIS_VOICE_TTS_API_KEY=<your-elevenlabs-key>

# Voice model and persona
export JARVIS_VOICE_TTS_MODEL=eleven_multilingual_v2
export JARVIS_VOICE_TTS_PERSONA=jarvis

# Disable vocal responses (fallback to text-only)
export JARVIS_VOICE_TTS_PROVIDER=silent
```

## Disabling Vocal Replies

If you want to disable vocal responses (fallback to text-only):

### Option 1: Environment Variable
```bash
export JARVIS_VOICE_TTS_PROVIDER=silent
```

### Option 2: Configuration
```python
# In jarvis/config.py, set:
voice_tts_provider: str = "silent"  # Disables TTS output
```

### Option 3: Runtime Check
```python
# In your application code:
if config.voice_tts_provider == "silent":
    # Skip vocal response generation
    log.info("Vocal responses disabled")
else:
    # Generate vocal response
    tts.speak(response_text)
```

## Operational Notes

### Rate Limiting
- ElevenLabs: 400 characters/month (free tier) or configured limit
- OpenAI TTS: ~500 requests/day (free tier)
- Piper (local): Unlimited (offline)

### Fallback Strategy
If TTS unavailable (no API key, quota exceeded):
1. Log warning: "TTS provider unavailable"
2. Fallback to text-only response
3. Continue with next command

### Performance
- **Piper (local)**: ~500ms per utterance (depends on text length)
- **ElevenLabs**: ~2-5s per utterance (network + generation)
- **OpenAI TTS**: ~3-8s per utterance (network + generation)

### Audio Output
- **Speaker**: System default audio device
- **Headphones**: Auto-detected if plugged in
- **Volume**: System volume control

## Testing Vocal Replies

### 1. Manual Test (REPL)
```python
from jarvis.voice_trigger import parse_voice_command

# Simulate voice input
voice_text = "respond vocally: what is the weather"
cmd = parse_voice_command(voice_text)

print(f"Command: {cmd}")
print(f"Type: {cmd.trigger_type}")
print(f"Payload: {cmd.payload}")
# Output:
# Command: VoiceCommand(trigger_type='respond_vocally', payload='what is the weather', ...)
# Type: respond_vocally
# Payload: what is the weather
```

### 2. Unit Tests
```bash
python -m pytest tests/test_voice_trigger.py::TestParseVoiceCommand -v
```

### 3. E2E Smoke Test
```bash
python scripts/smoke_test_vocal_agent.py

# Expected output:
# [TEST 1/4] Voice Command Parsing ✓
# [TEST 2/4] Agent Dialogue Routing (/hud/ask) ✓
# [TEST 3/4] Approval Integration ✓
# [TEST 4/4] Vocal Response Generation ~ (pending TTS)
```

### 4. Live Integration Test (WIP)
```bash
# Start the API
python -m jarvis.approval_api

# In another terminal, run the blocker smoke test
python scripts/smoke_test_vocal_agent.py

# Expected: All tests pass with real API running
```

## Next Steps (Roadmap)

1. **TTS Integration** (In Progress)
   - [ ] Wire `should_respond_vocally()` checks into `/hud/ask` endpoint
   - [ ] Implement TTS playback in browser (Web Audio API)
   - [ ] Add vocal response badge to HUD UI

2. **Voice Interruption (Barge-in)**
   - [ ] Add `interrupt` trigger: "interrupt: <command>"
   - [ ] Stop active TTS playback on new voice input
   - [ ] Prioritize microphone capture

3. **Advanced Triggers** (Future)
   - [ ] "confirm: <action>" → Auto-approve actions
   - [ ] "repeat: <command>" → Re-execute last command
   - [ ] Agent-specific triggers (jarvis/eva modes)

4. **Production Hardening**
   - [ ] API key rotation for TTS providers
   - [ ] Fallback TTS selection (e.g., local piper → ElevenLabs)
   - [ ] Audio quality tuning (sample rate, bitrate)
   - [ ] Accessibility features (speech rate, pitch control)

## Related Documentation

- [jarvis/approval_api.py](../jarvis/approval_api.py) — HTTP API endpoints
- [jarvis/brain.py](../jarvis/brain.py) — Agent dialogue logic
- [jarvis/voice_output.py](../jarvis/voice_output.py) — TTS provider adapters
- [docs/CORE_FEATURE_FINISH_PLAN.md](./CORE_FEATURE_FINISH_PLAN.md) — Broader voice stack roadmap

## Support

**Questions or issues?**
- Check `scripts/smoke_test_vocal_agent.py` for integration examples
- Review unit tests in `tests/test_voice_trigger.py` for expected behavior
- Enable debug logging: `export JARVIS_LOG_LEVEL=DEBUG`
