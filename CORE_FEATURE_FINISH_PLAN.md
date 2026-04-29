# Jarvis Core Feature Finish Plan

Purpose: one cohesive execution list to finish the core Jarvis product, not every future phase.

Definition of core for this plan:
- Local Jarvis runtime is stable and usable
- Voice interaction works end to end
- Command Center shows live useful data
- Approvals work reliably on local network devices
- Mobile and desktop UX are acceptable
- Core security, tests, and runbooks are in place

This plan intentionally excludes major expansion tracks like smart home, payments, telephony, trading, and desktop overlay until the core experience is complete.

---

## Exit Criteria

Jarvis core is considered complete when all of the following are true:

- [ ] A user can wake Jarvis or EVA, speak a request, and hear a response reliably
- [ ] Jarvis and EVA have distinct personas, voice output, and conversation context
- [ ] The Command Center displays live backend-driven data instead of placeholder values
- [ ] The HUD works on desktop, tablet, and phone without major usability issues
- [ ] Approval workflows work from the local machine and other trusted home-network devices
- [ ] Core endpoints have basic access protection and sane network restrictions
- [ ] The critical user flows have regression tests and smoke tests
- [ ] The main runbooks exist and are accurate

---

## Workstream 1: Voice Agent Completion

### 1.1 Agent-aware backend behavior
- [ ] Make `/hud/ask` accept and use the selected agent identity
- [ ] Define distinct system prompts for Jarvis and EVA
- [ ] Keep separate conversation state per agent
- [ ] Ensure agent switches do not leak prior agent context into the other persona
- [ ] Add backend response metadata showing which agent answered

### 1.2 Voice pipeline reliability
- [ ] Verify browser mic -> STT -> LLM -> TTS round-trip works consistently
- [ ] Add timeout handling for each voice stage
- [ ] Add graceful fallback when ElevenLabs is unavailable
- [ ] Wire local Piper fallback for TTS
- [ ] Decide whether browser Web Speech remains fallback or is replaced by Whisper

### 1.3 Wake phrase quality
- [ ] Verify Jarvis wake phrases trigger only Jarvis
- [ ] Verify EVA wake phrases trigger only EVA
- [ ] Reduce false positives while idle
- [ ] Add visible wake-listening state and last wake phrase feedback
- [ ] Add a user-facing toggle to disable wake listening quickly

### 1.4 Voice persistence and controls
- [ ] Persist per-agent voice preference cleanly
- [ ] Persist selected agent across reloads and restarts
- [ ] Add microphone selection if multiple input devices exist
- [ ] Add speaker/output selection if practical in current browser environment
- [ ] Add volume and mute controls for TTS playback

### 1.5 Voice tests
- [ ] Add regression test for agent switch command detection
- [ ] Add regression test for wake phrase routing
- [ ] Add regression test for fallback-to-text or fallback-TTS mode
- [ ] Add smoke test for `/hud/tts`
- [ ] Add smoke test for voice request flow from HUD

---

## Workstream 2: Command Center Live Wiring

### 2.1 Replace placeholder panels with real data
- [ ] Add Bitcoin snapshot endpoint in [jarvis/approval_api.py](jarvis/approval_api.py)
- [ ] Wire BTC panel to portfolio or market data source
- [ ] Add Social Monitoring endpoint backed by monitor/event data
- [ ] Add Oil and Gold endpoint with fallback behavior
- [ ] Add Tracking and Strategy endpoint with approvals and event throughput counts

### 2.2 Telemetry surfaces
- [ ] Replace top marquee placeholder text with real audit or telemetry data
- [ ] Replace bottom marquee placeholder text with system status data
- [ ] Show stale-data indicators when backend data is old
- [ ] Add panel-level loading states
- [ ] Add panel-level degraded/error states

### 2.3 Live updates
- [ ] Add stable SSE stream endpoint for HUD updates
- [ ] Subscribe Command Center panels to stream updates
- [ ] Add reconnect and backoff behavior for dropped connections
- [ ] Prevent noisy console errors when stream reconnects
- [ ] Add basic tests for stream payload shape

### 2.4 HUD tests
- [ ] Add schema tests for each HUD JSON endpoint
- [ ] Add smoke test for `/hud/cc`
- [ ] Add smoke test for `/hud/react`
- [ ] Add one integration test that verifies live panel data rendering

---

## Workstream 3: UX Completion

### 3.1 Mobile usability
- [ ] Finish phone layout cleanup beyond font scaling
- [ ] Fix touch target sizes for buttons and controls
- [ ] Make chat input and keyboard behavior reliable on mobile
- [ ] Ensure important controls stay visible above the mobile keyboard
- [ ] Validate portrait and landscape layouts on phone

### 3.2 Tablet and desktop polish
- [ ] Add tablet-specific layout behavior between phone and desktop widths
- [ ] Validate desktop layout at 100 percent and 125 percent scaling
- [ ] Validate ultrawide clipping and spacing behavior
- [ ] Fix any overlapping HUD elements at medium widths
- [ ] Make the status area and chat history easier to scan

### 3.3 Agent UX
- [ ] Make the message placeholder agent-aware
- [ ] Display current wake phrases in settings without polling hacks
- [ ] Show which agent is currently armed for wake listening
- [ ] Add clearer visual confirmation after switching agents
- [ ] Add clearer audio confirmation after switching agents

---

## Workstream 4: Approvals and Trusted Remote Use

### 4.1 Approval experience
- [ ] Verify approval list, approve, reject, and dispatch flows on the current server
- [ ] Add expiration handling that is visible in UI and CLI
- [ ] Add approval history view or archive summary
- [ ] Improve approval status visibility inside the Command Center
- [ ] Add tests for expired approval cleanup behavior

### 4.2 Home-network usage
- [ ] Confirm trusted-device access from phone and MacBook remains stable
- [ ] Document the home-network URL and binding behavior
- [ ] Add lightweight endpoint protection for approval actions
- [ ] Add origin checks or bearer-token auth for sensitive approval endpoints
- [ ] Validate firewall/network restrictions do not break intended devices

### 4.3 Reliability and ops
- [ ] Add health endpoint for server readiness
- [ ] Add alert or visible warning when approval queue stalls
- [ ] Add backup procedure for approvals and audit databases
- [ ] Add restore verification procedure
- [ ] Add smoke test for approval API startup and core routes

---

## Workstream 5: Core Security Hardening

### 5.1 Local-network security baseline
- [ ] Keep default binding and access model explicit in config and docs
- [ ] Add optional bearer-token auth for sensitive HUD write endpoints
- [ ] Add rate limiting to sensitive endpoints
- [ ] Add request validation for agent and voice endpoints
- [ ] Review CORS behavior for remote local-network access

### 5.2 Secrets and config hygiene
- [ ] Rotate any exposed keys currently stored in local files or chat logs
- [ ] Verify runtime loads keys from environment/config only
- [ ] Confirm ignored secret files stay out of git status
- [ ] Document key rotation steps in runbook form
- [ ] Add startup warnings for insecure production-like settings

---

## Workstream 6: Core Documentation

### 6.1 Must-have runbooks
- [ ] Create voice runbook covering setup, fallback, and troubleshooting
- [ ] Create Command Center runbook covering routes, data sources, and stream behavior
- [ ] Update approvals runbook for home-network usage
- [ ] Add quick recovery steps for voice failure, HUD failure, and approval failure
- [ ] Add mobile-access notes for phone and MacBook usage

### 6.2 User-facing docs
- [ ] Document all supported wake phrases
- [ ] Document agent switching commands
- [ ] Document current voice identities and fallback behavior
- [ ] Document known limitations of local-network-only access
- [ ] Cross-link new runbooks from [README.md](README.md) and [QUICKSTART.md](QUICKSTART.md)

---

## Workstream 7: Quality Gates

### 7.1 Critical regression coverage
- [ ] Agent switch behavior
- [ ] Wake phrase routing
- [ ] `/hud/ask` agent-awareness
- [ ] `/hud/tts` audio response path
- [ ] Approval lifecycle core paths
- [ ] HUD JSON endpoints
- [ ] SSE reconnect behavior

### 7.2 Final verification suite
- [ ] Add one command to run the core verification set
- [ ] Run targeted test suite for touched core features
- [ ] Run HUD smoke checks
- [ ] Run approval API smoke checks
- [ ] Capture final known-good output in docs/reports

---

## Recommended Execution Order

- [ ] 1. Finish agent-aware `/hud/ask`
- [ ] 2. Stabilize voice round-trip and fallback behavior
- [ ] 3. Replace Command Center placeholder data with real endpoints
- [ ] 4. Finish mobile and tablet usability pass
- [ ] 5. Harden approval flows for trusted remote devices
- [ ] 6. Add core security protections for sensitive endpoints
- [ ] 7. Write missing runbooks and user docs
- [ ] 8. Add regression coverage and final smoke suite

---

## Explicitly Deferred Until Core Is Done

- [ ] Smart home expansion
- [ ] Payments and virtual card workflows
- [ ] Telephony
- [ ] Trading integrations
- [ ] Desktop overlay and Tauri packaging
- [ ] Production internet exposure beyond home-network use

---

## Suggested First Sprint

- [ ] Make `/hud/ask` agent-aware
- [ ] Add per-agent system prompts and chat state
- [ ] Add regression tests for agent switch and wake routing
- [ ] Add `/hud/bitcoin`, `/hud/social`, `/hud/strategy` endpoints
- [ ] Render real data in three highest-value Command Center panels
- [ ] Finish phone layout and keyboard usability fixes
- [ ] Add voice runbook and update README links
