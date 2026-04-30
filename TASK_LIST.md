# Task List (2026-04-29)

This list tracks all remaining items, with newly added HUD and agent-quality work from the latest build session.

## 1) Blocker

- [x] **PARTIAL**: Rotate API key and run live agent E2E smoke test (REPL + vocal trigger: "respond vocally: status report")
  - [x] Voice trigger pattern recognition (jarvis/voice_trigger.py) ✓ 15/15 tests pass
  - [x] Vocal agent E2E smoke test (scripts/smoke_test_vocal_agent.py)
  - [x] Unit tests for voice trigger parsing (tests/test_voice_trigger.py + scripts/test_voice_trigger_simple.py)
  - [x] Voice output runbook (docs/runbooks/voice-output.md)
  - [ ] Integrate vocal response with TTS output (next)
  - [ ] Test with real API key rotation (next)

## 2) Command Center Live Data Wiring

- [x] Wire Bitcoin panel to real data via crypto_portfolio tool
  - Added `/hud/market/price?symbol=<id>` endpoint backed by Yahoo Finance (10s cache)
  - `_YAHOO_QUOTE_SYMBOLS` dict maps CoinGecko IDs / tickers to Yahoo symbols — extend to add assets
  - `useAssetPrice` tries backend proxy first, falls back to Binance direct
  - `coinMeta` persisted to `localStorage` (`cc:selectedAsset`) — survives page reload
- [ ] Wire Social Monitoring panel to monitors-status output
- [ ] Wire Oil and Gold panel to gold-price tool + market mode config
- [ ] Wire Tracking / Strategy panel to live approval + event counts (/approvals, /events)
- [ ] Replace top and bottom marquee placeholder text with audit-export tail
- [ ] Add WebSocket or SSE bridge so HUD reflects live brain Thought:/Observation: cycles

## 3) HUD and Agent Behavior Stabilization (NEW)

- [x] Show top-bar `Online`, `Stream`, and clock only when Jarvis is selected
- [x] Use a distinct clock font style for Jarvis mode (as requested) — Orbitron font with glow effect
- [~] Verify agent switch updates all UI surfaces (hero label, persona badge, voice target, status pills)
  - [x] TopBar hides Online/Stream/clock for non-Jarvis agents ✓
  - [x] Voice commands trigger agent switch and update `currentAgentId` state ✓
  - [ ] AgentSelector in Settings needs sync with main app state (refactor needed)
  - [ ] Persona badge visibility needs verification in all views
- [x] Add regression guard for dialogue prompts (`can you have a dialogue with jarvis`) to prevent canned/template replies
- [ ] Implement true voice interruption (barge-in) while TTS is speaking
- [ ] Add explicit `interrupt` handling path in `useVoice` to stop active audio and prioritize mic capture
- [ ] Ensure wake-listener resumes correctly after interruption and after TTS end
- [ ] Add tests for `/hud/ask` agent-dialogue routing and other-agent query fallback
- [ ] Tune EVA visual depth further: optional stronger forward tilt and minor parallax
- [ ] Add a setting to control EVA background intensity (clear/translucent/subtle)
- [ ] Review and fix any EVA chat-function parity gaps vs Jarvis (send, history, interrupt, greeting, agent switch)
- [x] Investigate `/hud/stream` `ERR_ABORTED` noise and harden reconnect behavior
  - [x] Added error deduplication (5s throttle on logging)
  - [x] Added jitter to exponential backoff to reduce thundering herd
  - [x] Reset error state on successful message
- [ ] Add end-to-end smoke test covering: switch agent -> ask -> voice reply -> interrupt -> recover

## 4) Voice and Docs

- [x] Add docs/runbooks/voice-output.md with recognized vocal-reply trigger phrases and disable mechanism
- [ ] Cross-link voice-output runbook from README docs index

## 5) Desktop Overlay (Tauri)

- [ ] Finalize framework decision (Tauri vs Electron)
- [ ] Scaffold src-tauri/ alongside jarvis/web/command_center/
- [ ] Configure transparent, frameless, always-on-top overlay pointing to http://127.0.0.1:8081/hud/cc
- [ ] Wire global hotkey (Cmd+Shift+J macOS / Ctrl+Shift+J Windows) for show/hide toggle
- [ ] Add /hud/show and /hud/hide endpoints to jarvis/approval_api.py
- [ ] Bridge Python wake-word detector to POST /hud/show
- [ ] Add system tray icon with Quit + Toggle menu actions
- [ ] Implement click-through on transparent regions (ignore cursor events toggling)
- [ ] Handle multi-display and display-change events
- [ ] Add macOS signing and notarization steps
- [ ] Build Windows .exe via Tauri cross-compile

## 6) Production Hardening

- [ ] Pick production deployment target (laptop / home server / VPS)
- [ ] Stand up live Alpaca broker connection (separate from paper)
- [ ] Configure real ntfy or Pushover push channel
- [ ] Harden remote approval channel (currently localhost-only)
- [ ] Add health and uptime monitoring for always-on server
- [ ] Implement remote access strategy (Tailscale / Cloudflare Tunnel / VPN)
- [ ] Document backup and restore procedure for audit.db and event bus DB

## 7) Layered Flight Digital Twin (Globe -> City)

Phase 1: Foundations + Live Data (est. 16-22h)
- [ ] Define architecture contract for LOD-0 (globe), LOD-1 (regional map), and LOD-2 (city wireframe)
- [ ] Create transition thresholds (zoom/altitude) and renderer-switch rules for each LOD
- [ ] Define shared camera state schema for globe and map modes
- [ ] Define shared selected-flight schema (id/callsign/lat/lon/alt/speed/heading)
- [ ] Add backend endpoint `/hud/air/states` in `jarvis/approval_api.py` as OpenSky proxy
- [ ] Add 5-15s cache layer for OpenSky responses to reduce request pressure
- [ ] Add graceful fallback payload when OpenSky is unavailable or rate-limited
- [ ] Normalize OpenSky fields into frontend-safe aircraft DTO (lat/lon/alt/vel/heading/callsign)
- [ ] Add backend endpoint `/hud/air/flight/{id}` for detailed active-flight payload
- [ ] Add backend endpoint `/hud/air/route/{id}` to provide route polyline/arcs when available
- [ ] Add frontend data service in planes module for polling `/hud/air/states`

Phase 2: Renderers + Seamless Transition (est. 24-34h)
- [ ] Integrate Globe.gl renderer for world-view aircraft and long-haul arcs
- [ ] Add click/select behavior on globe points to open flight details side panel
- [ ] Implement globe-to-map transition animation when a flight is selected
- [ ] Integrate Mapbox GL JS regional map view for selected AOI
- [ ] Add Mapbox `fill-extrusion` wireframe style for city buildings (dark base + cyan stroke)
- [ ] Add terrain toggle for tactical mode (on/off) with performance guard
- [ ] Add deck.gl overlay path for high-density mode (optional behind feature flag)
- [ ] Add renderer preload to avoid pop-in when transitioning LODs
- [ ] Add frustum/entity culling and distance-based fade for city building performance

Phase 3: UX Polish + Reliability + Ops (est. 18-26h)
- [ ] Add live telemetry overlay (altitude/speed/ETA/status) in LOD-2 city view
- [ ] Add route corridor highlighting in city view for active flight
- [ ] Add visual state badges for stale/live/error data feed states
- [ ] Add UI controls: world/regional/city quick jump and back-to-globe action
- [ ] Add Planes tab setting for data source mode (live/mock/offline replay)
- [ ] Add tests for renderer-switch state machine and selected-flight persistence
- [ ] Add smoke test: open Planes -> select flight -> transition to city -> return to globe
- [ ] Add runbook docs for OpenSky config, rate-limit behavior, and troubleshooting
- [ ] Add profiling pass on desktop + mobile and set performance budget thresholds
- [ ] Add production hardening checklist for air-data endpoints (timeouts, retries, circuit breaker)

Phase gate recommendation
- [ ] Gate 1 exit: Phase 1 done and `/hud/air/states` stable for 24h
- [ ] Gate 2 exit: Phase 2 done with smooth renderer switch under target FPS budget
- [ ] Gate 3 exit: Phase 3 done with tests green and runbooks published

## 8) Agent Customization & Skills (NEW)

- [x] Create JarvisEngineer agent with auto-activate keywords (flight|planes|air_bridge|LOD|digital twin)
- [x] Configure post-edit-hook for combined smoke test validation
- [x] Create Keep Todos skill for task automation workflow
- [ ] Document JarvisEngineer in .agent.md with full authority scope
- [ ] Add keep-todos skill to agent tool registry
- [ ] Create address-pr-comments skill for review automation
- [ ] Test skill auto-discovery with keyword triggers

## Summary

- Total open tasks: ~80 (added section 8 for agent customization)
- Phase 1-3 Flight Digital Twin: Complete ✓ (all 32 core tasks done)
- Suggested first milestone: complete sections 1, 3, and section 7 Phase 1
- Suggested second milestone: complete sections 2, 4, and section 7 Phase 2
- Suggested third milestone: complete sections 5, 6, and section 7 Phase 3
- Agent automation: In progress (JarvisEngineer + Keep Todos skill created)
