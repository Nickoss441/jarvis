# Wake-Word Integration Evaluation (Phase 2)

## Purpose

Document the recommended integration path for moving from the current voice scaffold to a real always-listening wake-word loop on macOS, while preserving deterministic behavior and existing safety boundaries.

## Current State Snapshot

The repository already has a usable scaffold:

- `jarvis/perception/voice/wake_word.py`
  - `DryRunWakeWordAdapter` matches the configured wake word against utf-8 text bytes.
  - `build_wake_word_adapter()` currently maps `local` and `porcupine` to dry-run behavior.
- `jarvis/perception/voice/stt.py`
  - STT providers are scaffolded but currently dry-run text decoding.
- `jarvis/perception/voice/__init__.py`
  - `build_voice_adapter_stack(...)` composes wake-word + STT + TTS adapters.
- `jarvis/__main__.py`
  - `voice-self-test` validates wake -> STT -> TTS round-trip shape and latency budget.

What is missing for production-like wake-word behavior:

- No live microphone capture loop.
- No frame-based wake engine (Porcupine/OpenWakeWord) wired to the adapter interface.
- No dedicated command that continuously listens and forwards transcripts into `brain.turn(...)`.
- No explicit runtime event emitted when wake-word triggers.

## Decision Summary

Recommended v1 path: **Porcupine-backed local wake-word detector with a conservative fallback to dry-run adapter**, followed by STT handoff to existing voice stack.

Why this path:

- Offline, low-latency wake detection suitable for laptop deployment.
- Small surface area change by implementing one adapter and one runner loop.
- Keeps existing architecture boundaries (`build_voice_adapter_stack`, `Brain.turn`, policy preflight, audit logging).

## Option Comparison

### Option A: Porcupine (recommended)

Pros:
- Mature wake-word SDK with low CPU profile.
- Good trigger stability for phrase-level wake words.
- Works well as a drop-in adapter implementation.

Cons:
- Additional runtime dependency and keyword model setup.
- Licensing and key management considerations.

### Option B: OpenWakeWord

Pros:
- Open model ecosystem and flexible wake-word configuration.
- Strong local-first story.

Cons:
- More pipeline tuning work to hit low false-positive rates.
- Potentially more CPU cost depending on model choice.

### Option C: Keep dry-run and rely on push-to-talk

Pros:
- Fastest to ship.
- Minimal dependencies.

Cons:
- Does not satisfy always-listening wake-word requirement.
- Not aligned with phase-2 interaction goals.

## Proposed Integration Plan

### Step 1: Add real wake adapter behind current interface

Add a provider-specific adapter in `jarvis/perception/voice/wake_word.py`:

- `PorcupineWakeWordAdapter(WakeWordAdapter)`
- Keep `DryRunWakeWordAdapter` as fallback.
- Update `build_wake_word_adapter(...)` routing:
  - `dry_run` -> dry-run adapter
  - `porcupine` -> Porcupine adapter (when dependency/config is present)
  - missing dependency or invalid config -> unsupported adapter with explicit error status

### Step 2: Add continuous voice loop command

Add a new command in `jarvis/__main__.py`, for example:

- `voice-listen [--max-turns N] [--timeout-seconds X]`

Loop behavior:

1. Open microphone stream.
2. Feed audio frames to wake adapter.
3. On trigger, collect short utterance window.
4. Transcribe with configured STT adapter.
5. Pass transcript into `Brain.turn(...)`.
6. Synthesize response with configured TTS adapter.
7. Repeat until stopped.

### Step 3: Emit runtime/audit events for observability

Emit deterministic events for key boundaries:

- `wake_word_triggered`
- `voice_stt_transcript`
- `voice_tts_response`

Include `correlation_id` per turn so voice-triggered actions remain traceable through approval and dispatch events.

### Step 4: Extend validation coverage

Add tests for:

- wake adapter provider routing and fallback behavior
- continuous loop argument parsing and stop conditions
- wake trigger event emission shape
- failure paths (mic unavailable, adapter unavailable, STT error)

## Configuration Additions (recommended)

Introduce explicit wake-word settings:

- `JARVIS_VOICE_WAKE_PROVIDER` (default `dry_run`, target `porcupine`)
- `JARVIS_VOICE_WAKE_SENSITIVITY` (float 0..1)
- `JARVIS_VOICE_WAKE_ACCESS_KEY` (if provider requires it)
- `JARVIS_VOICE_MIC_DEVICE` (optional input device id/name)

Keep current behavior if these are absent.

## Acceptance Gates

A wake-word path is considered ready when:

1. `voice-self-test` still passes deterministically.
2. New `voice-listen` command runs for at least 100 wake cycles in local test mode.
3. False-trigger rate and missed-trigger rate stay within agreed threshold over a fixed test window.
4. Every wake-triggered turn has correlation-linked audit visibility.

## Risks and Mitigations

Risk: false positives in noisy environments.
Mitigation: sensitivity tuning, cooldown window after trigger, optional VAD gate before STT.

Risk: microphone lock/device instability on macOS.
Mitigation: explicit retry/backoff and clear structured error payloads.

Risk: latency spikes for STT/TTS providers.
Mitigation: keep p95 gate in `voice-self-test`, add provider fallback where possible.

## Immediate Next Implementation Task

Implement `PorcupineWakeWordAdapter` in `jarvis/perception/voice/wake_word.py` and add focused unit tests in `tests/test_voice_scaffold.py` before introducing the continuous listener command.
