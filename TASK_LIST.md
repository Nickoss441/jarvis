# Task List (2026-04-30)

## 0) Session Carryover (Remaining)

- [ ] Finish mock->live migration validation for dashboard jitter replacement
- [ ] Fix AirBridge mock state label behavior and verify end-to-end
- [ ] Pull and configure Ollama `dolphin3:8b` model for runtime
- [ ] Update `.env.example` with finalized `D:\` path defaults
- [ ] Run full regression test suite and capture failures/action items

## 1) Blocker

- [x] Voice trigger pattern recognition ✓ 15/15 tests pass
- [x] Vocal agent E2E smoke test (scripts/smoke_test_vocal_agent.py)
- [x] Unit tests for voice trigger parsing
- [x] Voice output runbook (docs/runbooks/voice-output.md)
- [ ] Integrate vocal response with TTS output pipeline
- [ ] Test with real API key rotation

---

## 2) Command Center Live Data Wiring

- [x] Wire Bitcoin panel to real data via Yahoo Finance proxy
- [ ] Wire Social Monitoring panel to monitors-status output
- [ ] Wire Oil and Gold panel to gold-price tool + market mode config
- [ ] Wire Tracking / Strategy panel to live approval + event counts
- [ ] Replace top and bottom marquee placeholder text with audit-export tail
- [ ] Add WebSocket or SSE bridge so HUD reflects live brain Thought:/Observation: cycles

---

## 3) HUD and Agent Behavior

- [x] Top-bar Online/Stream/clock hidden for non-Jarvis agents
- [x] Orbitron clock font with glow effect in Jarvis mode
- [x] Regression guard for dialogue prompts
- [x] /hud/stream reconnect hardening (error dedup, jitter backoff)
- [ ] AgentSelector in Settings needs sync with main app state
- [ ] Persona badge visibility verification in all views
- [ ] Implement true voice interruption (barge-in) while TTS is speaking
- [ ] Add explicit `interrupt` handling path in `useVoice`
- [ ] Ensure wake-listener resumes correctly after interruption and after TTS end
- [ ] Add tests for `/hud/ask` agent-dialogue routing and other-agent query fallback
- [ ] Tune EVA visual depth: stronger forward tilt + minor parallax
- [ ] Add setting to control EVA background intensity (clear/translucent/subtle)
- [ ] Review and fix EVA chat-function parity gaps vs Jarvis
- [ ] Add end-to-end smoke test: switch agent → ask → voice reply → interrupt → recover

---

## 4) Voice and Docs

- [x] docs/runbooks/voice-output.md written
- [ ] Cross-link voice-output runbook from README docs index

---

## 5) Desktop Overlay (Tauri / Electron)

- [ ] Finalize framework decision (Tauri vs Electron)
- [ ] Scaffold src-tauri/ alongside jarvis/web/command_center/
- [ ] Configure transparent, frameless, always-on-top overlay → http://127.0.0.1:8081/hud/cc
- [ ] Wire global hotkey (Ctrl+Shift+J Windows / Cmd+Shift+J macOS)
- [ ] Add /hud/show and /hud/hide endpoints (currently stub — return success but do nothing)
- [ ] Bridge Python wake-word detector to POST /hud/show
- [ ] Add system tray icon with Quit + Toggle actions
- [ ] Implement click-through on transparent regions
- [ ] Handle multi-display and display-change events
- [ ] Add macOS signing and notarization steps
- [ ] Build Windows .exe via Tauri cross-compile

---

## 6) Production Hardening

- [ ] Pick production deployment target (laptop / home server / VPS)
- [ ] Stand up live Alpaca broker connection (separate from paper)
- [ ] Configure real ntfy or Pushover push channel
- [ ] Harden remote approval channel (currently localhost-only)
- [ ] Add health and uptime monitoring for always-on server
- [ ] Implement remote access strategy (Tailscale / Cloudflare Tunnel / VPN)
- [ ] Document backup and restore procedure for audit.db and event bus DB

---

## 7) Layered Flight Digital Twin (Globe → City)

### Phase 1 — Foundations + Live Data
- [ ] Define architecture contract for LOD-0 (globe), LOD-1 (regional map), LOD-2 (city wireframe)
- [ ] Create transition thresholds (zoom/altitude) and renderer-switch rules
- [ ] Define shared camera state schema for globe and map modes
- [ ] Define shared selected-flight schema (id/callsign/lat/lon/alt/speed/heading)
- [ ] Integrate Globe.gl renderer for world-view aircraft and long-haul arcs
- [ ] Add click/select behavior on globe to open flight details panel
- [ ] Add graceful fallback payload when data source unavailable or rate-limited

### Phase 2 — Renderers + Transition
- [ ] Implement globe-to-map transition animation when a flight is selected
- [ ] Integrate Mapbox GL JS regional map view for selected AOI
- [ ] Add Mapbox fill-extrusion wireframe style for city buildings (dark + cyan stroke)
- [ ] Add terrain toggle for tactical mode with performance guard
- [ ] Add deck.gl overlay path for high-density mode (feature flag)
- [ ] Add renderer preload to avoid pop-in when transitioning LODs
- [ ] Add frustum/entity culling and distance-based fade for city building performance

### Phase 3 — UX Polish + Reliability
- [ ] Add live telemetry overlay (altitude/speed/ETA/status) in city view
- [ ] Add route corridor highlighting in city view for active flight
- [ ] Add visual state badges for stale/live/error data feed states
- [ ] Add UI controls: world/regional/city quick jump and back-to-globe action
- [ ] Add Planes tab setting for data source mode (live/mock/offline replay)
- [ ] Add tests for renderer-switch state machine and selected-flight persistence
- [ ] Add smoke test: open Planes → select flight → transition to city → return to globe
- [ ] Add runbook docs for OpenSky config, rate limits, and troubleshooting
- [ ] Add profiling pass on desktop + mobile and set performance budget thresholds

### Phase Gates
- [ ] Gate 1 exit: Phase 1 done and /hud/air/states stable for 24h
- [ ] Gate 2 exit: Phase 2 done with smooth renderer switch under target FPS budget
- [ ] Gate 3 exit: Phase 3 done with tests green and runbooks published

---

## 8) Agent Customization & Skills

- [x] Create JarvisEngineer agent with auto-activate keywords
- [x] Configure post-edit-hook for combined smoke test validation
- [x] Create keep-todos skill for task automation workflow
- [ ] Document JarvisEngineer in .agent.md with full authority scope
- [ ] Add keep-todos skill to agent tool registry
- [ ] Create address-pr-comments skill for review automation
- [ ] Test skill auto-discovery with keyword triggers

---

## 9) Security — Remaining (from 2026-04-30 audit)

### High
- [ ] approval_api.py — Zero authentication on /hud/*, /approvals/*, /ipc/*, /trade/* endpoints (design-level, needs auth middleware or token gate)
- [ ] approval_api.py:3482 — /hud/globe/config sends Mapbox + OWM API keys to any browser client
- [ ] air_bridge.py:128 — OpenSky credentials sent over plain HTTP Basic Auth; enforce HTTPS or disable when no creds set
- [ ] approval_api.py:372 — Private IP 192.168.0.171 hardcoded in logs (replace with config-driven host)

### Medium
- [ ] app.js:484 — EventSource reconnects forever with no max-retry cap or user notification
- [ ] sandbox.py:57 — HOME=/tmp hardcoded; invalid on Windows, breaks subprocess environment
- [ ] sandbox.py:142 — Retry loop on BlockingIOError with no sleep (tight spinlock)
- [ ] call_phone.py:66 — Phone number validation only checks + prefix; accepts +abc and similar junk
- [ ] payments.py:99 — Float tolerance 0.01 on line items; crafted values can bypass budget check
- [ ] app.js:2163 — localStorage.setItem() calls without try/catch; silently breaks in private/incognito mode
- [ ] app.js:1462 — setInterval in useBars not re-subscribed if ms prop changes; stale timer persists
- [ ] approval_api.py — 30+ bare `except Exception: pass` blocks swallowing failures silently
- [ ] gold_trade.py:191 — Live execution raises RuntimeError but no phase gate prevents calling it
- [ ] wallet.py:131 — Negative balance allowed for credit cards but not loan accounts; logic inconsistency

### Low / Polish
- [ ] app.js:145 — Both branches of ternary render "▼"; dead logic, one branch should be "▲"
- [ ] app.js:1485 — EVA wake phrase detected and agent switchable but eva.html is orphaned (never shown)
- [ ] voice_trigger.py:11 — Regex `.+?` can match empty string; use `.+`
- [ ] app.js:986 — Reddit fetched directly from browser; CORS fails in many regions; needs backend proxy
- [ ] gold_trade.py:191 — Live execution path raises RuntimeError but is still reachable
- [ ] config.py:8 — Silent `except ImportError: pass` on dotenv; user never knows .env was not loaded
- [ ] app.js:4798 — Approvals iframe src hardcoded to "/"
- [ ] calendar_read.py:73 — Malformed calendar lines silently skipped with no logging
- [ ] app.js:852 — setTimeout(() => setFlash(null)) × 3 instances with no cleanup on unmount

---

## 10) Code Quality — Remaining

- [ ] brain.py — Add structured logging (replace removed debug prints with proper logger calls)
- [ ] approval_api.py — Audit and reduce 30+ bare `except Exception: pass` blocks
- [ ] audit.py — Wrap json.loads() in recent() with explicit error handling per row
- [ ] air_bridge.py:214 — Verify alt_baro == "ground" handling against adsb.lol spec; document or remove
- [ ] ollama_adapter.py:173 — Bare `except: pass` swallows all Ollama startup errors; log at WARNING
- [ ] mic.py:173 — Whisper model load blocks indefinitely on first run; add progress indicator or timeout

---

## Summary

| Section | Open | Done |
|---|---|---|
| 1 — Blockers | 2 | 4 |
| 2 — Live Data Wiring | 5 | 1 |
| 3 — HUD / Agent | 10 | 5 |
| 4 — Voice / Docs | 1 | 1 |
| 5 — Desktop Overlay | 11 | 0 |
| 6 — Production | 7 | 0 |
| 7 — Flight Digital Twin | 22 | 0 |
| 8 — Agent / Skills | 4 | 3 |
| 9 — Security (remaining) | 20 | 11 (fixed 2026-04-30) |
| 10 — Code Quality | 6 | 0 |
| **Total** | **88** | **25** |
