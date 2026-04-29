# Jarvis — Lacking Items & Missing Functionality

Comprehensive inventory of incomplete features, gaps, and unimplemented tasks across all phases.

---

## Phase 2: Voice & Audio (Currently Partial)

### Voice Infrastructure
- [ ] Whisper STT integration (speech-to-text)
  - [ ] Model download and caching
  - [ ] Real-time transcription from microphone
  - [ ] Fallback to browser Web Speech API
  - [ ] STT error handling (background noise, timeout)
  
- [ ] Piper TTS fallback (local text-to-speech)
  - [ ] Model download and caching
  - [ ] Fallback when ElevenLabs unavailable
  - [ ] Voice selection from Piper voices

- [ ] Voice quality testing
  - [ ] Latency benchmarks (STT + LLM + TTS round-trip)
  - [ ] Audio codec quality comparison
  - [ ] Network bandwidth optimization

### Agent Voice Personality ✅ Partial
- [x] Jarvis male voice (Eric)
- [x] EVA female voice (The Asians)
- [ ] Per-agent system prompts/personalities
  - [ ] Jarvis: Technical, direct, professional tone
  - [ ] EVA: Sophisticated, strategic, elegant tone
- [ ] Behavioral directives per agent
- [ ] Agent-specific response templates
- [ ] Separate chat history per agent
- [ ] Per-agent voice persistence

### Wake Word & Detection ✅ Partial
- [x] Wake phrase detection infrastructure
- [x] Agent-specific wake phrases
  - [x] Jarvis: "hey jarvis", "jarvis wake up", "wake up jarvis", "ok jarvis"
  - [x] EVA: "hey eva", "eva wake up", "wake up eva", "ok eva"
- [ ] Custom wake word training
- [ ] Wake word confidence threshold tuning
- [ ] False positive reduction
- [ ] Wake word performance metrics/stats
- [ ] Option to record custom wake words

### Audio I/O
- [ ] Microphone device selection
- [ ] Speaker device selection
- [ ] Volume control for TTS output
- [ ] Audio input level meter (visual feedback)
- [ ] Ambient noise detection before STT
- [ ] Echo cancellation for video calls
- [ ] Audio buffer management

### Voice Testing & Docs
- [ ] Voice integration runbook (docs/runbooks/voice-output.md)
- [ ] Wake word troubleshooting guide
- [ ] TTS voice selection guide
- [ ] STT accuracy testing procedure
- [ ] Voice quality benchmarks documentation
- [ ] Unit tests for STT pipeline
- [ ] Unit tests for TTS pipeline
- [ ] E2E test for voice command routing

---

## Phase 3: Smart Home (Not Started)

### Home Assistant Integration
- [ ] Home Assistant API client
  - [ ] Entity discovery
  - [ ] State polling
  - [ ] Event subscription
  - [ ] Action/service calls
  
- [ ] Core Smart Home Tools
  - [ ] `smart_home_lights` (on/off, brightness, color)
  - [ ] `smart_home_locks` (lock/unlock with audit)
  - [ ] `smart_home_climate` (temperature, HVAC mode)
  - [ ] `smart_home_garage` (open/close with confirmation)
  - [ ] `smart_home_alarm` (arm/disarm with passcode)
  - [ ] `smart_home_camera` (snapshot, recent events)

- [ ] Home Scene Management
  - [ ] Predefined scenes ("movie mode", "night mode", etc.)
  - [ ] Scene composition (multiple device changes)
  - [ ] Scheduled automation triggers

- [ ] Policy Enforcement
  - [ ] Gated access to dangerous operations (locks, alarm)
  - [ ] Confirmation requirements for critical changes
  - [ ] Time-based restrictions (no door unlock after midnight)
  - [ ] Approval queue for high-risk operations

- [ ] Home Status Dashboard
  - [ ] Current device states panel
  - [ ] Last action history
  - [ ] Upcoming automations
  - [ ] Energy usage summary

- [ ] Testing
  - [ ] Mock Home Assistant server tests
  - [ ] Policy validation tests
  - [ ] E2E integration tests

---

## Phase 4: Approvals & Notifications (Partial)

### Approval Service ✅ Partial
- [x] Approval store and lifecycle management
- [x] Approval service layer
- [x] Correlation IDs across events
- [ ] Approval persistence improvements
  - [ ] Add expiration timestamps
  - [ ] Cleanup of expired approvals (background job)
  - [ ] Approval archive (read-only historical storage)
  
### Notification Channels (Incomplete)
- [ ] ntfy.sh integration
  - [ ] Setup and authentication
  - [ ] Topic management
  - [ ] Message formatting
  - [ ] Reconnection handling
  
- [ ] Pushover integration
  - [ ] API key configuration
  - [ ] Message priority levels
  - [ ] Notification sounds per action type
  
- [ ] Twilio SMS integration (Phase 6 dependency)
  - [ ] Phone number validation
  - [ ] SMS rate limiting
  - [ ] Delivery confirmation

### Approval UI
- [ ] Web approvals dashboard
  - [ ] Pending approvals list
  - [ ] Action buttons (approve/reject/details)
  - [ ] Time-to-expiry indicator
  - [ ] Approval history/archive view
  
- [ ] Mobile approvals interface
  - [ ] Responsive design for phones
  - [ ] Quick approve/reject buttons
  - [ ] Push notification tap-through
  
- [ ] Approval Polling
  - [ ] Long-polling endpoint for approvals
  - [ ] SSE stream for real-time updates
  - [ ] WebSocket fallback

### Approval Rules Engine
- [ ] Auto-approve rules (bypass approval for low-risk operations)
  - [ ] List safe operations
  - [ ] Time-based auto-approve windows
  - [ ] Per-operation thresholds
  
- [ ] Approval quotas
  - [ ] Daily/weekly approval limits
  - [ ] Cost limits requiring extra confirmation
  - [ ] Rate limits per tool

---

## Phase 5: Payments (Not Started)

### Payment Infrastructure
- [ ] Stripe integration
  - [ ] Account setup and API keys
  - [ ] Webhook receiver
  - [ ] Payment intent creation
  - [ ] Refund handling
  
- [ ] Virtual Card (Stripe Issuing)
  - [ ] Card creation and management
  - [ ] Spending limits (€100 cap)
  - [ ] Transaction monitoring
  - [ ] Card termination

### Payments Ledger
- [ ] Ledger data model
  - [ ] Transaction records
  - [ ] Balance tracking
  - [ ] Reconciliation fields
  
- [ ] Payment tools
  - [ ] `send_payment` (Stripe transfer)
  - [ ] `check_balance` (account status)
  - [ ] `list_transactions` (history)
  
- [ ] Payment confirmation flow
  - [ ] Approval queue required
  - [ ] Amount verification
  - [ ] Recipient validation
  - [ ] Pre-payment audit

### Payments Policy
- [ ] Daily spend limit enforcement
- [ ] Recipient allowlist/blocklist
- [ ] Payment method restrictions
- [ ] Currency conversion rules
- [ ] Fee disclosure before approval

### Payments Testing
- [ ] Stripe test mode harness
- [ ] Mock payment responses
- [ ] Ledger reconciliation tests
- [ ] Policy validation tests

---

## Phase 6: Telephony & Trading (Not Started)

### Telephony (Twilio)
- [ ] Twilio client setup
  - [ ] Account configuration
  - [ ] Phone number provisioning
  - [ ] API credentials
  
- [ ] Voice call tools
  - [ ] `call_phone` (outbound call with disclosure)
  - [ ] `send_sms` (text message)
  - [ ] `transcribe_voicemail` (to text)
  
- [ ] AI Disclosure Flow
  - [ ] Pre-call recording/consent
  - [ ] Mandatory disclosure message
  - [ ] Call opt-out mechanism
  - [ ] Audit trail of all calls
  
- [ ] Telephony Routing
  - [ ] Caller ID spoofing prevention
  - [ ] Voicemail transcription
  - [ ] Call recording storage
  - [ ] HIPAA-compliant retention

### Trading (Alpaca/IBKR)
- [ ] Broker integration
  - [ ] Paper trading mode
  - [ ] Live trading mode (with gating)
  - [ ] Account information retrieval
  - [ ] Position tracking
  
- [ ] Trading tools
  - [ ] `create_trade` (place order with confirmation)
  - [ ] `close_position` (sell/close)
  - [ ] `get_account_status` (balance, margin)
  - [ ] `get_portfolio_summary` (holdings)
  
- [ ] Trading Risk Controls
  - [ ] Position size limits (2% equity cap)
  - [ ] Daily loss limits (auto-pause on drawdown)
  - [ ] Leverage restrictions
  - [ ] Restricted symbol lists
  
- [ ] Trading Safety Gates
  - [ ] Mandatory approval for live trades
  - [ ] Pre-trade verification
  - [ ] Post-trade reconciliation
  - [ ] Trade review checkpoint (first 25 trades)
  
- [ ] Trading Analytics
  - [ ] P&L calculation
  - [ ] Performance metrics
  - [ ] Trade entry/exit analysis
  - [ ] Slippage tracking

### Trading Testing
- [ ] Paper trading smoke tests
- [ ] Live trading dry-run tests
- [ ] Risk control validation tests
- [ ] Reconciliation tests

---

## Command Center HUD (Partial ✅)

### Live Data Integration
- [ ] Bitcoin panel data source
  - [ ] API endpoint `/hud/bitcoin`
  - [ ] Crypto portfolio integration
  - [ ] Price update frequency
  - [ ] Stale-data indicator
  
- [ ] Social Monitoring panel
  - [ ] Monitor status aggregation endpoint
  - [ ] Delta calculation
  - [ ] Trend bar rendering
  
- [ ] Oil & Gold panel
  - [ ] Market data source (gold-price tool, market config)
  - [ ] Price display formatting
  - [ ] Percentage change calculation
  - [ ] Profitable day/week indicator
  
- [ ] Tracking & Strategy panel
  - [ ] Approval counts endpoint
  - [ ] Pending/approved/rejected breakdown
  - [ ] Event throughput metric
  
- [ ] System Telemetry
  - [ ] Top marquee: audit log tail (real-time)
  - [ ] Bottom marquee: system status (memory, CPU, uptime)

### HUD Live Updates
- [ ] SSE endpoint for streaming updates
  - [ ] `/hud/stream` endpoint
  - [ ] Heartbeat mechanism
  - [ ] Reconnection handling
  - [ ] Backoff strategy
  
- [ ] Frontend SSE subscription
  - [ ] Panel update handlers
  - [ ] Fallback polling if SSE fails
  - [ ] Data staleness detection

### HUD Reliability
- [ ] API timeout handling (all endpoints)
- [ ] Panel loading states
- [ ] Panel degraded/error states
- [ ] Graceful fallbacks
- [ ] Offline mode support

### HUD Responsive Design ✅ Partial
- [x] Mobile font scaling
- [ ] Tablet layout optimization (768px-1024px)
- [ ] Ultrawide support (>1920px)
- [ ] Touch-friendly button sizing
- [ ] Landscape/portrait orientation handling

### HUD Testing
- [ ] JSON endpoint schema tests
- [ ] Route serving smoke tests
- [ ] Data contract tests
- [ ] SSE stream tests
- [ ] Mobile layout tests

---

## Desktop Overlay (Tauri) (Not Started)

### Framework & Build
- [ ] Tauri project scaffold
  - [ ] Rust build configuration
  - [ ] TypeScript/React frontend
  - [ ] IPC bridge setup
  
- [ ] Development Workflow
  - [ ] `make overlay-dev` command
  - [ ] Hot reload during development
  - [ ] Debug tools

### Window Management
- [ ] Frameless transparent window
  - [ ] Always-on-top behavior
  - [ ] Click-through for transparent regions
  - [ ] Click-focus toggle mode
  
- [ ] Multi-display support
  - [ ] Display detection
  - [ ] Position persistence
  - [ ] Add/remove event handling
  - [ ] DPI scaling per display

### Global Hotkeys
- [ ] Windows: Ctrl+Shift+J (show/hide HUD)
- [ ] macOS: Cmd+Shift+J (show/hide HUD)
- [ ] Show/hide endpoints in approval_api
- [ ] Hotkey customization

### System Tray
- [ ] Tray icon creation
- [ ] Show action
- [ ] Hide action
- [ ] Quit action
- [ ] Status indicator (active/idle)

### HUD Server Integration
- [ ] Startup check for HUD availability
- [ ] Fallback if server unavailable
- [ ] Auto-reconnect on server restart

### Build & Packaging
- [ ] Windows signed executable
  - [ ] Code signing certificate
  - [ ] Build pipeline
  
- [ ] macOS notarization & signing
  - [ ] Developer ID certificate
  - [ ] Notarization process
  - [ ] Gatekeeper compatibility
  
- [ ] Installer packages
  - [ ] Windows MSI
  - [ ] macOS DMG
  - [ ] Auto-updater mechanism

---

## Documentation Gaps

### Voice Runbooks
- [ ] Voice setup guide (docs/runbooks/voice-setup.md)
- [ ] Wake word troubleshooting
- [ ] TTS voice selection guide
- [ ] Voice output disabling procedure
- [ ] STT accuracy optimization

### Smart Home Runbooks
- [ ] Home Assistant setup (docs/runbooks/home-assistant-setup.md)
- [ ] Entity configuration guide
- [ ] Policy enforcement examples
- [ ] Safety checklists

### Payments Runbooks
- [ ] Stripe account setup (docs/runbooks/payments-setup.md)
- [ ] Virtual card creation
- [ ] Payment approval workflow
- [ ] Dispute resolution procedure

### Trading Runbooks
- [ ] Paper trading setup (docs/runbooks/trading-setup.md)
- [ ] Live trading activation (gated)
- [ ] Risk control validation
- [ ] Trade review procedures
- [ ] Emergency stop procedure

### Telephony Runbooks
- [ ] Twilio setup (docs/runbooks/telephony-setup.md)
- [ ] Disclosure message templates
- [ ] Call recording procedures
- [ ] Privacy and HIPAA compliance

### General Documentation
- [ ] Data dictionary (all event types, tool schemas)
- [ ] API reference (all endpoints)
- [ ] Error code catalog
- [ ] Performance benchmarks
- [ ] Architecture evolution notes

---

## Testing Gaps

### Unit Tests
- [ ] STT pipeline tests
- [ ] TTS pipeline tests
- [ ] Voice command routing tests
- [ ] Home Assistant mock tests
- [ ] Payment ledger tests
- [ ] Trading risk control tests
- [ ] Approval expiration tests

### Integration Tests
- [ ] Voice end-to-end (wake word → STT → LLM → TTS)
- [ ] Home automation workflows
- [ ] Approval notification delivery
- [ ] Payment settlement flow
- [ ] Trading order execution
- [ ] Telephony disclosure flow

### E2E Smoke Tests
- [ ] HUD page load and render
- [ ] Real-time data updates
- [ ] Desktop overlay startup
- [ ] Approval workflow
- [ ] Voice command execution

### Performance Tests
- [ ] Voice latency benchmarks
- [ ] HUD data fetch latency
- [ ] Database query performance
- [ ] Concurrent approval handling
- [ ] Streaming update throughput

---

## Deployment & Ops

### Deployment Targets
- [ ] Define production environment (laptop/server/VPS)
- [ ] Production config profile creation
- [ ] Environment-specific secrets management
- [ ] Rollback procedures

### Monitoring & Alerts
- [ ] Health check endpoint
- [ ] Uptime monitoring
- [ ] Error rate alerts
- [ ] Performance degradation alerts
- [ ] Approval queue stall detection

### Backup & Recovery
- [ ] approvals.db backup strategy
- [ ] audit.db backup strategy
- [ ] Restore verification procedure
- [ ] Retention policies
- [ ] Disaster recovery drill

### Security Hardening
- [ ] HTTPS/SSL for remote access (if needed)
- [ ] API authentication on approval endpoints
- [ ] CORS policy configuration
- [ ] Rate limiting on all endpoints
- [ ] Input validation and sanitization
- [ ] XSS/CSRF protection
- [ ] SQL injection prevention (parameterized queries)

### Key Rotation
- [ ] API key rotation procedures
- [ ] Key storage security
- [ ] Key expiration automation
- [ ] Compromise response plan

---

## Project Infrastructure

### CI/CD
- [ ] GitHub Actions workflows
- [ ] Automated test running
- [ ] Linting and format checks
- [ ] Build pipeline
- [ ] Automatic release notes

### Code Quality
- [ ] Coverage targets (>80% for critical paths)
- [ ] Code review process documentation
- [ ] Pre-commit hooks enforcement
- [ ] Dependency update automation
- [ ] Security scanning

### Telemetry & Metrics
- [ ] Custom metrics infrastructure
- [ ] Latency tracking
- [ ] Error rate tracking
- [ ] Tool usage statistics
- [ ] Performance trending

---

## Summary Stats

| Category | Total | Blocked | In Progress | To Do |
|----------|-------|---------|-------------|-------|
| Phase 2: Voice | 25 | 0 | 4 | 21 |
| Phase 3: Smart Home | 20 | 0 | 0 | 20 |
| Phase 4: Approvals | 22 | 0 | 2 | 20 |
| Phase 5: Payments | 20 | 0 | 0 | 20 |
| Phase 6: Telephony & Trading | 35 | 0 | 0 | 35 |
| HUD & Desktop | 30 | 0 | 3 | 27 |
| Documentation | 18 | 0 | 0 | 18 |
| Testing | 18 | 0 | 0 | 18 |
| Ops & Infrastructure | 25 | 0 | 0 | 25 |
| **TOTAL** | **213** | **0** | **9** | **204** |

---

**Last Updated:** 2026-04-29
**Created By:** Copilot Agent
**Status:** Active backlog for priority sequencing
