# Jarvis

A personal AI assistant with a browser-based HUD, European flight tracking, approval workflows, voice I/O, and a full perception layer. Runs locally on your laptop — Claude Sonnet 4.6 as the brain, Ollama as the optional fast-path router.

## Repository

- GitHub: `https://github.com/Nickoss441/jarvis`
- Branch: `main`

```bash
git add -A && git commit -m "your message" && git push origin main
```

---

## What's built

| Area | Status | Notes |
|---|---|---|
| Brain (Claude Sonnet 4.6) | Live | Agent loop, tool use, audit chain |
| Ollama fast-path router | Live | Routes simple turns to local LLM before hitting Claude |
| Command Center HUD | Live | React SPA at `/hud/cc` — chat, crypto, news, approvals |
| EVA HUD surface | Live | Alternate personality at `/hud/eva` |
| European flight tracker | Live | `/hud/planes` — Leaflet map, watchlist, real adsbdb.com lookups |
| Approval workflow | Live | Queue, push notifications, gated dispatch |
| Voice I/O | Live | Wake word → Whisper STT → Piper/ElevenLabs TTS |
| Perception layer | Live | Calendar, RSS, filesystem, webhook, vision monitors |
| Desktop overlay | Scaffolded | Electron — transparent always-on-top window |
| Payments | Dry-run | Stripe integration ready, gated by phase flag |
| Telephony | Dry-run | Twilio, with mandatory AI disclosure |
| Trading | Dry-run/Paper | Alpaca paper broker wired |
| Smart home | Gated | Home Assistant integration |
| Spotify | Live | Playback control via voice or chat |

---

## Quickstart

```bash
cd jarvis
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# edit .env — set ANTHROPIC_API_KEY at minimum
python3 -m jarvis approvals-api
```

Then open:
- `http://127.0.0.1:8080/hud/cc` — Command Center
- `http://127.0.0.1:8080/hud/planes` — European Flight Tracker
- `http://127.0.0.1:8080/hud/eva` — EVA surface

> **Port fallback:** if 8080 is busy the server tries 8081–8089 and prints the actual URL.

### Minimum `.env`

```env
ANTHROPIC_API_KEY=sk-ant-...
JARVIS_USER_NAME=Nick
```

---

## HUD Surfaces

### Command Center (`/hud/cc`)
Full-screen glassmorphic dashboard with:
- **Chat** — direct message to Jarvis or EVA
- **Crypto** — live Bitcoin/ETH/SOL prices via Yahoo Finance proxy
- **News** — live feed from Reuters, BBC, TechCrunch, CoinDesk
- **Approvals** — pending action queue with approve/reject
- **Market data** — gold, oil, S&P 500
- **Voice** — wake-word listener, agent-switch ("switch to eva")
- **Splash screens** — Jarvis (cyan scan animation) and EVA (purple pulse animation), 4.5s each

### EVA (`/hud/eva`)
Alternate AI personality surface — same capabilities, separate visual identity (purple/pink theme).

### European Flight Tracker (`/hud/planes`)

- Leaflet map defaulting to Europe `[52°N, 10°E]`, zoom 5
- Live ADS-B data from **adsb.lol** (European bbox, no auth) with OpenSky as primary
- Up to 150 aircraft, prioritised: airborne with callsign → airborne → ground
- Dead-reckoning — positions extrapolated every second between 15s polls
- Icon cache by `(color, size, rounded heading)` — no SVG object churn per tick
- **Left sidebar**: Watched Flights + European Airspace live list
- **Detail card** (floating, center): aircraft silhouette SVG, real origin/destination from adsbdb.com callsign lookup, altitude/speed/heading, vert rate, squawk, ICAO24
- **Watchlist**: persisted to `jarvis-data/air_watchlist.json`, survives page reload
- Route bar updates async — shows `…` while fetching, fills in real airport codes (e.g. `AMS → LHR`)

---

## Architecture

```
jarvis/
├── brain.py               Agent loop — perceive → plan → preflight → dispatch → observe
├── cli.py                 REPL + tool registration
├── config.py              .env-driven config with secret provider abstraction
├── audit.py               Append-only SQLite, SHA-256 hash chain
├── approval.py            Approval queue store
├── approval_service.py    Approval boundary — request, approve, reject, dispatch
├── approval_api.py        HTTP API surface (all /hud/* and /approvals/* routes)
├── air_bridge.py          OpenSky + adsb.lol proxy, adsbdb.com detail/route lookup
├── air_data_schema.py     AircraftDTO, FlightDetailDTO, RouteDTO, AirStatesPayload
├── memory.py              In-process + file-backed conversation store
├── ollama_adapter.py      Local LLM router with model selection and retry
├── voice_trigger.py       Vocal-reply pattern parser
├── monitor_runner.py      Background perception monitors
├── runtime/               Turn orchestration scaffold
├── perception/
│   └── voice/
│       ├── mic.py         Wake word → Whisper STT → brain → TTS pipeline
│       └── tts.py         Piper (local ONNX) + ElevenLabs + FallbackTTSAdapter
├── tools/                 ~55 tools — open, gated, financial, voice, vision
└── web/
    ├── command_center/    Command Center + EVA + Planes HUD (vanilla JS + React)
    │   ├── app.js         Main React app (Jarvis + EVA dual-personality)
    │   ├── planes.html    European flight tracker
    │   ├── air_service.js Frontend polling service
    │   ├── air_state.js   Shared aircraft state
    │   └── renderers/
    │       ├── globe.js   Leaflet map with DR animation and icon cache
    │       ├── manager.js LOD renderer manager
    │       └── base.js    Abstract renderer base
    ├── hud_react/         React HUD viewport
    └── jarvis_home/       Home surface

overlay/                   Electron desktop overlay (scaffolded)
static/logo/               jarvis-logo.svg (cyan hex eye), eva-logo.svg (purple diamond)
scripts/                   Smoke tests, demo scripts, health checks
tests/                     Unit tests (audit, policy, voice trigger, air bridge)
docs/runbooks/             Operational runbooks
```

---

## Phase Flags

All gated capabilities are off by default. Enable per phase:

| Flag | Adds |
|---|---|
| `JARVIS_PHASE_VOICE=true` | Wake word, Whisper STT, Piper/ElevenLabs TTS |
| `JARVIS_PHASE_SMART_HOME=true` | Home Assistant read/write tools |
| `JARVIS_PHASE_APPROVALS=true` | Approval queue, gated dispatch |
| `JARVIS_PHASE_PAYMENTS=true` | Payments ledger, Stripe (requires APPROVALS) |
| `JARVIS_PHASE_TELEPHONY=true` | Twilio outbound calling (requires APPROVALS) |
| `JARVIS_PHASE_TRADING=true` | Alpaca paper/live trading (requires APPROVALS) |

---

## Tools (55 total)

**Open (no approval):** `web_search`, `web_fetch`, `notes`, `recall`, `calendar_read`, `mail_draft`, `weather_here`, `weather_now`, `eta_to`, `location_current`, `events_recent`, `news`, `gold`, `crypto_portfolio`, `market_data`, `spotify`, `desktop_control`, `vision_observe`, `solana_tx_lookup`, `solana_wallet_activity`, `youtube`, `user_preferences`, `app_list`, `app_status`, `financial_dashboard`, `budget_forecast`, `expense_analytics`, `cash_flow_forecaster`, `debt_payoff_planner`, `goal_tracker`, `retirement_planner`, `portfolio_optimizer`, `tax_optimizer`, `financial_recommendations`, `financial_independence_planner`, `home_purchase_planner`, `college_savings_planner`, `emergency_fund_planner`, `rent_vs_buy_analyzer`, `sinking_fund_planner`, `subscription_manager`, `travel`, `wallet`, `alert_manager`

**Gated (require approval):** `message_send`, `call_phone`, `payments`, `trade`, `gold_trade`, `install_app`, `uninstall_app`, `home_assistant`, `reservation_call`, `sandbox`

---

## API Endpoints

### Air / Flight
| Method | Path | Description |
|---|---|---|
| GET | `/hud/air/states` | All aircraft (live, stale, or error state) |
| GET | `/hud/air/flight/{icao24}` | Aircraft detail from adsbdb.com (operator, type, registration) |
| GET | `/hud/air/route/{icao24}?cs={callsign}` | Origin/destination from adsbdb.com callsign lookup |
| GET | `/hud/air/watchlist` | Tracked ICAO IDs |
| POST | `/hud/air/watchlist` | Add `{"icao_id":"3c6444"}` to watchlist |
| DELETE | `/hud/air/watchlist/{id}` | Remove from watchlist |

### HUD / Chat
| Method | Path | Description |
|---|---|---|
| GET | `/hud/cc` | Command Center SPA |
| GET | `/hud/planes` | European flight tracker |
| GET | `/hud/eva` | EVA surface |
| GET | `/hud/stream` | SSE brain thought stream |
| GET | `/hud/ask?q=...` | One-shot question to Jarvis brain |
| GET | `/health` | Health + readiness check |
| GET | `/hud/version` | Version info |
| GET | `/hud/news` | Live news feed |
| GET | `/hud/metals` | Gold/silver/platinum prices |
| GET | `/hud/market/price?symbol=btc` | Yahoo Finance price proxy |

### Approvals
| Method | Path | Description |
|---|---|---|
| GET | `/approvals/pending` | List pending approvals |
| POST | `/approvals/{id}/approve` | Approve `{"reason":"..."}` |
| POST | `/approvals/{id}/reject` | Reject `{"reason":"..."}` |
| POST | `/approvals/dispatch` | Dispatch approved items |

### Chat inbound
| Method | Path | Description |
|---|---|---|
| POST | `/chat/inbound` | `{"account_id","token","source","text"}` |
| POST | `/chat/twilio` | Twilio SMS webhook |

### Static assets
| Method | Path | Description |
|---|---|---|
| GET | `/static/logo/jarvis-logo.svg` | Jarvis cyan hex-eye logo |
| GET | `/static/logo/eva-logo.svg` | EVA purple diamond-eye logo |

---

## CLI Commands

```bash
# Start the server
python3 -m jarvis approvals-api [host] [port]

# Chat REPL
python3 -m jarvis

# Approvals
python3 -m jarvis approvals-list
python3 -m jarvis approvals-approve <id> [reason]
python3 -m jarvis approvals-reject <id> [reason]
python3 -m jarvis approvals-dispatch
python3 -m jarvis approvals-seed [count]

# Perception
python3 -m jarvis monitor-run-once
python3 -m jarvis events-list [limit] [--unprocessed]
python3 -m jarvis events-stats
python3 -m jarvis events-process [limit]
python3 -m jarvis events-actions [limit] [kind] [--correlation-id <id>]
python3 -m jarvis events-prune-actions [days]

# Location
python3 -m jarvis location-update <lat> <lon> [--source name] [--accuracy-m n]
python3 -m jarvis location-last

# Voice
python3 -m jarvis voice-self-test [--iterations N] [--max-roundtrip-ms X]

# Vision / iPhone bridge
python3 -m jarvis vision-listen [source] [host] [port]
python3 -m jarvis vision-shortcut-template [url]
python3 -m jarvis vision-shortcut-guide [url]
python3 -m jarvis vision-analyze <file|base64|-> [--no-faces] [--no-colors] [--no-landmarks]
python3 -m jarvis vision-self-test [json|multipart|binary|all] [--report] [--fail-fast]

# Audit
python3 -m jarvis audit-verify
python3 -m jarvis audit-correlation <id> [limit]

# Trading
python3 -m jarvis trade-performance-report [paper|live|dry_run]
python3 -m jarvis trade-review-artifact

# Webhooks
python3 -m jarvis webhook-listen [source] [host] [port]
```

---

## Key Config Variables

```env
# Required
ANTHROPIC_API_KEY=

# Identity
JARVIS_USER_NAME=Nick
JARVIS_DEPLOYMENT_TARGET=laptop

# Phase gates (all default false)
JARVIS_PHASE_VOICE=false
JARVIS_PHASE_SMART_HOME=false
JARVIS_PHASE_APPROVALS=false
JARVIS_PHASE_PAYMENTS=false
JARVIS_PHASE_TELEPHONY=false
JARVIS_PHASE_TRADING=false

# Server
JARVIS_APPROVALS_API_HOST=127.0.0.1
JARVIS_APPROVALS_API_PORT=8080

# Voice
JARVIS_VOICE_WAKE_WORD=jarvis
JARVIS_VOICE_STT_PROVIDER=faster-whisper
JARVIS_VOICE_TTS_PROVIDER=piper
# ELEVENLABS_API_KEY=

# Flight data (no key needed — adsb.lol is free)
# Optional: add OpenSky credentials for higher quota
OPENSKY_USER=
OPENSKY_PASS=

# Spotify
# SPOTIFY_CLIENT_ID=
# SPOTIFY_CLIENT_SECRET=
# SPOTIFY_REDIRECT_URI=http://localhost:8888/callback

# Solana
HELIUS_API_KEY=
HELIUS_NETWORK=mainnet

# Approvals / push
# NTFY_TOPIC=
# PUSHOVER_APP_TOKEN=
# PUSHOVER_USER_KEY=

# Trading
JARVIS_TRADES_MODE=dry_run
JARVIS_TRADING_PAPER_BROKER=alpaca
# ALPACA_API_KEY=
# ALPACA_API_SECRET=

# Email
# JARVIS_SMTP_HOST=smtp.gmail.com
# JARVIS_SMTP_PORT=587
# JARVIS_SMTP_USER=
# JARVIS_SMTP_PASS=
```

Full reference: `.env.example`

---

## Data Files Created at Runtime

```
~/.jarvis/audit.db              Hash-chained audit log
~/.jarvis/approvals.db          Approval queue
~/.jarvis/event-bus.db          Perception event bus
~/.jarvis/message-outbox.jsonl  Dry-run outbound messages
~/.jarvis/calls-log.jsonl       Dry-run call log
~/.jarvis/payments-ledger.jsonl Dry-run payments
~/.jarvis/trades-log.jsonl      Trade log
~/.jarvis/dropzone/             Watched directory for filesystem monitor
~/jarvis-notes/                 Markdown notes vault

jarvis-data/air_watchlist.json  Persisted flight watchlist
```

---

## Perception Layer

Five background monitors emit structured events to an SQLite event bus:

| Monitor | Trigger | Event kind |
|---|---|---|
| Calendar | New VEVENT in `.ics` | `calendar_event` |
| RSS | New feed item | `rss_item` |
| Filesystem | New file in dropzone | `filesystem_new_file` |
| Webhook | HTTP POST | `webhook_event` |
| Vision | Camera frame POST | `vision_frame` |

Deterministic automation rules fire on events:
- `webhook_github` → `message_send` approval alert
- `filesystem_new_file` → `message_send` approval alert
- `vision_frame` → `message_send` alert with face/color summary

Safeguards: idempotency, per-kind hourly caps, retention cleanup.

---

## Voice Pipeline

```
wake word (speech_recognition)
    → Whisper STT (faster-whisper, local)
        → brain.turn()
            → TTS (Piper ONNX local  |  ElevenLabs API)
                → sounddevice playback
```

Vocal reply trigger phrase: `respond vocally: <your message>`

TTS adapters: `PiperLocalTTSAdapter` (ONNX, offline), `ElevenLabsTTSAdapter` (API), `FallbackTTSAdapter` (primary → fallback), `DryRunTTSAdapter` (testing).

---

## Desktop Overlay (Electron)

Scaffolded in `overlay/`. Transparent, frameless, always-on-top window pointing at `http://127.0.0.1:8080/hud/cc`.

```bash
cd overlay
npm install
npm start
```

Pending: global hotkey (Ctrl+Shift+J), `/hud/show` + `/hud/hide` endpoints, click-through regions, system tray.

---

## Tests

```bash
pytest tests/

# With lint
make verify
```

Covers: audit log (append, verify, tamper), policy engine (blocked tools/domains/paths), voice trigger parsing, air bridge normalization.

---

## Runbooks

| File | Topic |
|---|---|
| `docs/runbooks/approvals.md` | Approval workflow |
| `docs/runbooks/kill-switch.md` | Emergency stop |
| `docs/runbooks/key-rotation.md` | API key rotation |
| `docs/runbooks/hud-commands.md` | HUD routes reference |
| `docs/runbooks/voice-output.md` | TTS config, trigger phrases, disable |
| `docs/runbooks/opensky-integration.md` | Flight data config and rate limits |
| `docs/runbooks/live-trading-unlock.md` | Live trading unlock checklist |
| `docs/runbooks/paper-trading-review.md` | Paper performance review |
| `docs/runbooks/incident-response.md` | Incident response |

---

## What's Next

| Priority | Item |
|---|---|
| High | Wire Oil/Gold and Social panels to live data in Command Center |
| High | EVA/Jarvis chat parity and agent-switch sync in Settings |
| Medium | Voice barge-in (interrupt TTS mid-sentence) |
| Medium | Finish Electron overlay (hotkey, tray, click-through) |
| Low | Production hardening (Tailscale/Cloudflare remote access, uptime monitoring) |
