# Jarvis — Phase 1

The brain + open tools + audit log slice of the architecture in `ARCHITECTURE.md`. Chat-only, runs on your laptop, no API keys beyond Anthropic required.

## What's in this phase

- **Brain.** Agent loop on Claude Sonnet 4.6 with tool use.
- **Open tools.** Web search (DuckDuckGo), web fetch (httpx + readability), local markdown notes vault, recall over the audit log.
- **Audit log.** SQLite, append-only, SHA-256 hash chain — every observation, tool call, and result is logged and tamper-evident.
- **Policy engine.** Deterministic pre-flight check before each tool call (path traversal, blocked domains, blocked tools).
- **CLI REPL.** Talk to it from a terminal.

## What's NOT in this phase (by design)

| Phase | Adds |
|-------|------|
| 2 | Voice (wake word + Whisper STT + Piper TTS) |
| 3 | Smart home (Home Assistant) |
| 4 | Approval surface (push notifications) + email send |
| 5 | Payments — Stripe Checkout + virtual card with €100 cap |
| 6 | Telephony (Twilio + AI disclosure) + paper trading |

If you ask phase-1 Jarvis to call someone or buy something, it will tell you it can't yet.

## Phased Capability Matrix

| Phase | Core capabilities | Primary flags |
|-------|-------------------|---------------|
| 1 | Chat runtime, open tools, deterministic policy, hash-chained audit | none (default) |
| 2 | Voice scaffolding (wake/STT/TTS providers) | `JARVIS_PHASE_VOICE=true` |
| 3 | Smart-home control paths with policy checks | `JARVIS_PHASE_SMART_HOME=true` |
| 4 | Approval queue APIs, approval-dispatch workflows, gated messaging | `JARVIS_PHASE_APPROVALS=true` |
| 5 | Payments policy/ledger workflows and reconciliation hooks | `JARVIS_PHASE_PAYMENTS=true` |
| 6 | Telephony disclosure flow and trading safety gates | `JARVIS_PHASE_TELEPHONY=true`, `JARVIS_PHASE_TRADING=true` |

## Quickstart by Phase

Phase 1 (core runtime):

```bash
python3 -m jarvis
```

Phase 4 (approval workflows):

```bash
export JARVIS_PHASE_APPROVALS=true
python3 -m jarvis approvals-list
python3 -m jarvis approvals-dispatch
```

Phase 5 (payments dry-run):

```bash
export JARVIS_PHASE_APPROVALS=true
export JARVIS_PHASE_PAYMENTS=true
export JARVIS_PAYMENTS_MODE=dry_run
```

Phase 6 (telephony + trading dry-run/paper):

```bash
export JARVIS_PHASE_APPROVALS=true
export JARVIS_PHASE_TELEPHONY=true
export JARVIS_PHASE_TRADING=true
export JARVIS_CALL_PHONE_MODE=dry_run
export JARVIS_TRADES_MODE=dry_run
```

## Runbooks, ADRs, and Templates

- Runbooks:
    - `docs/runbooks/approvals.md`
    - `docs/runbooks/kill-switch.md`
    - `docs/runbooks/incident-response.md`
    - `docs/runbooks/key-rotation.md`
    - `docs/runbooks/hud-commands.md`
    - `docs/runbooks/wake-word-integration-evaluation.md`
    - `docs/runbooks/paper-trading-review.md`
    - `docs/runbooks/app-lifecycle-smoke-test.md`
- Review artifact templates:
    - `docs/reviews/paper-performance-review-template.md`
- Voice recording templates:
    - `docs/voice-recording-scripts.md`
- ADR index:
    - `docs/adrs/README.md`
- Dry-run gated-tool demos:
    - `scripts/demo/demo_message_send.sh`
    - `scripts/demo/demo_call_phone.sh`
    - `scripts/demo/demo_payments.sh`
    - `scripts/demo/demo_trade.sh`
- Policy templates:
    - `policy-templates/strict.yaml`
    - `policy-templates/balanced.yaml`
    - `policy-templates/permissive.yaml`

## Setup

```bash
cd jarvis
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env

# equivalent bootstrap shortcut
make setup
```

Open `.env` and set at minimum:
- `ANTHROPIC_API_KEY` — get from https://console.anthropic.com
- `JARVIS_USER_NAME` — what Jarvis calls you

Project foundation default:
- Deployment target: `laptop` (`JARVIS_DEPLOYMENT_TARGET`)
- Voice stack: `local` using `faster-whisper + Piper` (`JARVIS_VOICE_STACK`)

Optional phase flags (all default to `false`):
- `JARVIS_PHASE_VOICE`
- `JARVIS_PHASE_SMART_HOME`
- `JARVIS_PHASE_APPROVALS`
- `JARVIS_PHASE_PAYMENTS`
- `JARVIS_PHASE_TELEPHONY`
- `JARVIS_PHASE_TRADING`

Open-tool scaffold settings:
- `JARVIS_CALENDAR_ICS` (default: `~/.jarvis/calendar.ics`)
    - On macOS, if this file is missing, `calendar_read` falls back to Apple Calendar via `osascript`.
- `install_app` tool (sandbox phase only): allowlisted macOS app installs via Homebrew cask with official download URL fallback
- `app_status` tool (sandbox phase only): check if an allowlisted macOS app is installed and detect its version
- `app_list` tool (sandbox phase only): list all allowlisted macOS apps and their installation status (inventory discovery)
- `uninstall_app` tool (sandbox phase only): allowlisted macOS app removal with approval gating (brew or manual fallback)
- `JARVIS_MAIL_DRAFTS_PATH` (default: `~/.jarvis/mail-drafts.jsonl`)
- `JARVIS_DROPZONE_DIR` (default: `~/.jarvis/dropzone`)
- `JARVIS_RSS_FEED_URL` (optional; supports `file://` and `https://`)
- `JARVIS_WEBHOOK_HOST` (default: `127.0.0.1`)
- `JARVIS_WEBHOOK_PORT` (default: `9010`)
- `JARVIS_WEBHOOK_SOURCE` (default: `default`)
- `JARVIS_WEBHOOK_SECRET` (optional HMAC secret; validates `X-Jarvis-Signature`)
- `JARVIS_WEBHOOK_PATH_KIND_MAP` (optional path routing map, e.g. `/github:webhook_github,/ifttt:webhook_ifttt`)
- `JARVIS_VISION_HOST` (default: `127.0.0.1`)
- `JARVIS_VISION_PORT` (default: `9021`)
- `JARVIS_VISION_SOURCE` (default: `iphone`)
- `JARVIS_VISION_SECRET` (optional HMAC secret for posted camera frames)
- `JARVIS_VISION_MAX_FRAME_BYTES` (default: `2000000`)
- `JARVIS_FORCE_VISION_LANDMARKS` (optional; on Python 3.13+, set to `1`/`true`/`yes`/`on` to force Apple Vision landmarks path)
- `JARVIS_EVENT_ALERT_CHANNEL` (default: `slack`)
- `JARVIS_EVENT_ALERT_RECIPIENT` (default: `#ops`)
- `JARVIS_EVENT_ALERTS_MAX_PER_HOUR_BY_KIND` (optional, e.g. `webhook_github:10`)
- Trade review thresholds:
    - `JARVIS_TRADING_REVIEW_MIN_TRADING_DAYS` (default: `20`)
    - `JARVIS_TRADING_REVIEW_MIN_TRADES` (default: `100`)
    - `JARVIS_TRADING_REVIEW_MIN_WIN_RATE` (default: `0.5`)
    - `JARVIS_TRADING_REVIEW_MIN_PROFIT_FACTOR` (default: `1.0`)
    - `JARVIS_TRADING_REVIEW_MIN_AVG_R_MULTIPLE` (default: `0.0`)
    - `JARVIS_TRADING_REVIEW_MAX_ANOMALIES` (default: `0`)

Helius / Solana settings:
- `HELIUS_API_KEY` (required for Solana tools)
- `HELIUS_NETWORK` (`mainnet` or `devnet`, default: `mainnet`)

Helius-backed tools available in chat:
- `solana_tx_lookup`
- `solana_wallet_activity`
- `solana_enhanced_tx_lookup` (`/v0/transactions`)
- `solana_enhanced_address_transactions` (`/v0/addresses/{address}/transactions`)

Outbound messaging dry-run settings:
- `JARVIS_MESSAGE_SEND_MODE` (default: `dry_run`)
- `JARVIS_MESSAGE_OUTBOX` (default: `~/.jarvis/message-outbox.jsonl`)

Outbound calling dry-run settings:
- `JARVIS_CALL_PHONE_MODE` (default: `dry_run`)
- `JARVIS_CALLS_LOG_PATH` (default: `~/.jarvis/calls-log.jsonl`)
- Frozen disclosure template:
    - `Hello, this is an AI assistant calling on behalf of {user_name} to {purpose}. Is that alright to proceed?`

Payments tool settings:
- `JARVIS_PAYMENTS_MODE` (default: `dry_run`)
- `JARVIS_PAYMENTS_LEDGER` (default: `~/.jarvis/payments-ledger.jsonl`)
- Budget cap: $10,000 per transaction

Trading tool settings:
- `JARVIS_TRADES_MODE` (default: `dry_run`)
- `JARVIS_TRADES_LOG` (default: `~/.jarvis/trades-log.jsonl`)
- Position cap: 10,000 units per order

Approval queue settings:
- `JARVIS_APPROVAL_DB` (default: `~/.jarvis/approvals.db`)
- `JARVIS_APPROVALS_TTL_SECONDS` (default: `900`)
- `JARVIS_APPROVALS_DISPATCH_COOLDOWN_SECONDS` (default: `0`)
- `JARVIS_APPROVALS_DISPATCH_MAX_PER_RUN` (default: `25`)
- `JARVIS_APPROVALS_DISPATCH_COOLDOWN_BY_KIND` (default: empty)
- `JARVIS_APPROVAL_CHANNEL` (default decision: `ntfy`)

Project foundation defaults:
- Push/approval channel: `ntfy`
- Paper-trading broker: `alpaca` (`JARVIS_TRADING_PAPER_BROKER`)

Phase-gated module settings:
- Voice: `JARVIS_VOICE_WAKE_WORD` (default: `jarvis`), `JARVIS_VOICE_STT_PROVIDER` (default: `faster-whisper`), `JARVIS_VOICE_TTS_PROVIDER` (default: `piper`)
- Smart home: `JARVIS_HOME_ASSISTANT_URL`, `JARVIS_HOME_ASSISTANT_TOKEN`, `JARVIS_HOME_ASSISTANT_TIMEOUT_SECONDS` (default: `10`)
- Telephony: `JARVIS_TELEPHONY_PROVIDER` (default: `dry_run`), `JARVIS_TELEPHONY_CALLER_ID`, `JARVIS_TELEPHONY_DISCLOSURE_TEMPLATE`

Secret provider abstraction:
- `JARVIS_SECRET_PROVIDER` (default: `env`, supported: `env`, `keychain`, `1password`/`op`, `bitwarden`/`bw`)
- Keychain: `JARVIS_KEYCHAIN_SERVICE` (default: `jarvis`), optional per-key account override `JARVIS_KEYCHAIN_ACCOUNT_<KEY>`
- 1Password: per-key refs via `JARVIS_OP_REF_<KEY>` (used with `op read`)
- Bitwarden: per-key item IDs via `JARVIS_BW_ITEM_<KEY>` (used with `bw get password`)

Secrets currently fetched through this provider path in `Config.from_env()`:
- `ANTHROPIC_API_KEY`
- `HELIUS_API_KEY`
- `JARVIS_HOME_ASSISTANT_TOKEN`
- `JARVIS_WEBHOOK_SECRET`
- `JARVIS_VISION_SECRET`

Note: `message_send`, `call_phone`, `payments`, and `trade` are policy-gated and require phase flags (`JARVIS_PHASE_APPROVALS`, `JARVIS_PHASE_TELEPHONY`, `JARVIS_PHASE_PAYMENTS`, `JARVIS_PHASE_TRADING`).

## Perception Layer

The perception layer uses an event bus and monitors to make Jarvis continuously aware of external state. The event bus is SQLite-backed and append-only.

Each perception event now uses one unified envelope:
- `source` — emitting monitor or ingress surface
- `timestamp` — event creation time
- `correlation_id` — trace key for downstream approvals and automation history
- `payload` — event-specific structured data

Event bus settings:
- `JARVIS_EVENT_BUS_DB` (default: `~/.jarvis/event-bus.db`)

Monitors are background workers that observe external systems and emit structured events:
- **Calendar Monitor** — Parses `calendar.ics` and emits newly added VEVENT entries
- **RSS Monitor** — Polls RSS/Atom feeds and emits newly seen items
- **Webhook Monitor** — Receives HTTP POST events and emits `webhook_event` records
    - Optional signature validation (`X-Jarvis-Signature: sha256=...`)
    - Optional path-based event kind routing
- **Vision Ingest Monitor** — Receives camera frame payloads and emits `vision_frame` records
    - Intended for iPhone bridge apps and phone-relayed Ray-Ban Meta captures
    - Stores compact frame metadata (hash, size, labels/text), not raw image blobs
- **Filesystem Monitor** — Watches a drop zone directory and emits newly created files

Perception CLI commands:
- `python3 -m jarvis monitor-run-once` — run configured monitors once
- `python3 -m jarvis events-stats` — print aggregate event bus counts
- `python3 -m jarvis events-list [limit] [--unprocessed]` — list recent/unprocessed events
- `python3 -m jarvis events-process [limit]` — apply deterministic event automation rules
- `python3 -m jarvis events-actions [limit] [event_kind|--kind <event_kind>] [--correlation-id <id>]` — inspect automation history
- `python3 -m jarvis events-prune-actions [days]` — prune old automation history rows
- `python3 -m jarvis location-update <latitude> <longitude> [--source <name>] [--accuracy-m <meters>]` — ingest latest GPS coordinates into EventBus
- `python3 -m jarvis location-last` — print most recent ingested GPS coordinates
- `python3 -m jarvis trade-performance-report [paper|live|dry_run|--mode <mode>]` — summarize persisted trade performance metrics and audit review signals
- `python3 -m jarvis voice-self-test [--iterations N] [--max-roundtrip-ms X]` — run local voice round-trip stability and latency gate for Phase 2

Location-aware open tools in chat:
- `location_current` — fetch latest stored coordinates and freshness metadata
- `weather_here` — weather at latest stored coordinates (no manual lat/lon needed)
- `eta_to` — route ETA from latest stored coordinates to destination
- `python3 -m jarvis webhook-listen [source] [host] [port]` — start local webhook receiver
- `python3 -m jarvis vision-listen [source] [host] [port]` — start local camera frame receiver
- `python3 -m jarvis vision-shortcut-template [url]` — print iPhone Shortcut request template
- `python3 -m jarvis vision-shortcut-guide [url]` — print step-by-step iPhone Shortcut setup
- `python3 -m jarvis vision-self-test [json|multipart|binary|all] [--with-secret] [--report] [--fail-fast] [--max-modes N] [--modes csv] [--output-file path.json] [--output-format json|jsonl]` — run end-to-end local vision pipeline self-test
- `python3 -m jarvis vision-self-test-summary <input.jsonl> [--mode json|multipart|binary|all] [--last N] [--percentiles csv] [--strict] [--max-invalid-lines N] [--ema-alpha A] [--max-invalid-line-rate-delta X] [--max-invalid-line-rate-ema X]` — summarize JSONL self-test history
- `python3 -m jarvis vision-analyze <file|base64|-> [--no-faces] [--no-colors] [--no-landmarks] [--max-colors N]` — detect faces, dominant colors, and facial landmarks from a frame image

Current deterministic event automation rules:
- `webhook_github` -> create a `message_send` approval alert to `JARVIS_EVENT_ALERT_RECIPIENT`
- `filesystem_new_file` -> create a `message_send` approval alert
- `vision_frame` -> create a `message_send` approval alert with frame metadata plus face/color summary when available

Automation safeguards:
- **Idempotency:** duplicate events with identical kind/source/payload are processed once.
- **Per-kind throttling:** optional hourly caps prevent burst alert spam.
- **Retention cleanup:** old automation action rows can be pruned by age.
- **Perception quality gates** (vision alerts only):
  - Face detection is included in alert only when all detected faces meet minimum confidence threshold (`JARVIS_VISION_MIN_FACE_CONFIDENCE`, default: 0.8).
  - Color analysis is included only when total color coverage meets minimum threshold (`JARVIS_VISION_MIN_COLOR_COVERAGE`, default: 0.8, meaning 80% of frame must be covered by detected colors).
  - Low-confidence detections are gracefully omitted from alerts rather than failing them.

Phase 2 voice acceptance:
- Run `python3 -m jarvis voice-self-test --iterations 20 --max-roundtrip-ms 50` and require `ok: true`.
- Use `latency_ms.p95` from command output as the deterministic round-trip latency gate.

## Run

```bash
python3 -m jarvis

# equivalent shortcut
make run
```

```
Jarvis (phase 1) — type 'quit' to exit, 'reset' to clear conversation.

you > what's the weather in Amsterdam tomorrow?
jarvis > Looking that up...
[runs web_search + web_fetch under the hood]
jarvis > Tomorrow in Amsterdam: 14°C, partly cloudy, light wind from the west.
```

REPL commands:
- `reset` — clear conversation memory (audit log is preserved)
- `quit` / `exit` — leave

Approval queue commands:
- `python3 -m jarvis approvals-list` — list pending approvals
- `python3 -m jarvis approvals-approve <id> [reason]` — approve a queued action
- `python3 -m jarvis approvals-reject <id> [reason]` — reject a queued action
- `python3 -m jarvis approvals-dispatch` — process approved actions via provider
- `python3 -m jarvis approvals-seed [count]` — create demo approvals for testing (default: 3)
- `python3 -m jarvis approvals-api [host] [port]` — run local HTTP approval API with glassmorphic command-center UI
    - **Port fallback:** if the requested port (default `8080`) is busy, the server automatically tries the next 10 ports and prints e.g. `Requested port 8080 busy; using http://127.0.0.1:8081 instead.` Bind to a specific port by passing `host port` explicitly.
  - **App Lifecycle Panel:** Request app status checks, installations, and removals via the web UI
  - **Approval Queue Table:** Review and approve pending actions
  - **Chat Interface:** Direct messaging with Jarvis brain
  - Navigate to `/` for approvals, `/hud/cc` for the command center, `/hud/globe` for the React HUD viewport
  - **Port fallback:** if the requested port (default `8080`, set via `JARVIS_APPROVALS_API_PORT`) is busy, the server automatically tries the next 9 ports (`8080–8089`). The actual URL is printed at startup. If all 10 are occupied the process exits with an error.
  - **Network exposure guard:** the server refuses to bind to any non-localhost address unless `--expose` is passed. The approval API has no authentication — do not expose it on an untrusted network.
- `python3 -m jarvis hud-run [--width N] [--height N] [--opacity X] [--duration-ms N]` — run the transparent PyQt HUD overlay shell
- `python3 -m jarvis trade-review-artifact [--reviewer <name>] [--strategy-version <ver>] [--output <path>]` — generate the live-unlock markdown review record plus audit/replay/performance artifacts
- `python3 -m jarvis monitor-run-once` — run monitor cycle once
- `python3 -m jarvis events-stats` — summarize event bus
- `python3 -m jarvis events-list [limit] [--unprocessed]` — inspect events
- `python3 -m jarvis events-process [limit]` — process unprocessed events through deterministic rules
- `python3 -m jarvis events-actions [limit] [event_kind|--kind <event_kind>] [--correlation-id <id>]` — view automation actions (approval_created, duplicate, throttled, no_rule)
- `python3 -m jarvis events-prune-actions [days]` — delete old automation action rows
- `python3 -m jarvis location-update <latitude> <longitude> [--source <name>] [--accuracy-m <meters>]` — ingest a fresh location update
- `python3 -m jarvis location-last` — view latest known location update
- `python3 -m jarvis webhook-listen [source] [host] [port]` — run webhook receiver
- `python3 -m jarvis vision-listen [source] [host] [port]` — run vision/camera listener
- `python3 -m jarvis vision-shortcut-template [url]` — print iPhone request template
- `python3 -m jarvis vision-shortcut-guide [url]` — print iPhone setup guide
- `python3 -m jarvis vision-self-test [json|multipart|binary|all] [--with-secret] [--report] [--fail-fast] [--max-modes N] [--modes csv] [--output-file path.json] [--output-format json|jsonl]` — run local vision pipeline self-test
- `python3 -m jarvis vision-self-test-summary <input.jsonl> [--mode json|multipart|binary|all] [--last N] [--percentiles csv] [--strict] [--max-invalid-lines N] [--ema-alpha A] [--max-invalid-line-rate-delta X] [--max-invalid-line-rate-ema X]` — summarize self-test history artifacts
- `python3 -m jarvis vision-analyze <file|base64|-> [--no-faces] [--no-colors] [--no-landmarks] [--max-colors N]` — detect faces, dominant colors, and facial landmarks from a frame image

HUD surfaces:
- `python3 -m jarvis hud-run --width 680 --height 150 --opacity 0.77 --duration-ms 2500` — launch the native PyQt overlay HUD
- `python3 -m jarvis approvals-api` then open `/hud/react` — launch the browser-based React HUD served by the approval API
- See `docs/runbooks/hud-commands.md` for the current HUD routes, examples, and runtime notes

Trace-specific automation history examples:

```bash
# all actions for one correlation chain
python3 -m jarvis events-actions 50 --correlation-id corr-123

# combine kind + correlation for tighter narrowing
python3 -m jarvis events-actions 50 webhook_github --correlation-id corr-123

# equivalent explicit flag style
python3 -m jarvis events-actions 50 --kind webhook_github --correlation-id corr-123
```

## iPhone and Ray-Ban Meta Camera Bridge

Ray-Ban Meta does not currently expose a direct local raw camera API for this app, so the practical path is:
- Capture through iPhone (or Ray-Ban media synced to iPhone)
- Post frame metadata and optional image payload to Jarvis

Start the listener:

```bash
python3 -m jarvis vision-listen iphone 127.0.0.1 9021
```

Generate a ready-to-paste Shortcut request template:

```bash
python3 -m jarvis vision-shortcut-template
```

Generate a step-by-step iPhone Shortcut build guide:

```bash
python3 -m jarvis vision-shortcut-guide
```

Analyze a frame image for faces and dominant colors:

```bash
python3 -m jarvis vision-analyze frame.jpg
python3 -m jarvis vision-analyze frame.jpg --max-colors 3
python3 -m jarvis vision-analyze - --no-faces < frame.jpg.b64
```

Analyze with landmarks disabled (gaze direction, head pose, etc.):

```bash
python3 -m jarvis vision-analyze frame.jpg --no-landmarks
```

The vision-analyze command detects:
- **Faces**: bounding boxes and confidence scores (via Apple Vision.framework)
- **Dominant colors**: top N colors, percentages, hex values (via Pillow pixel bucketing)
- **Facial landmarks** (default): eyes, nose, mouth positions, derived features like gaze direction (center/left/right/up/down) and head pose (tilt + nod)

Note: on some macOS Python 3.13 + PyObjC stacks, repeated landmark requests can crash the interpreter. Jarvis now defaults to a safe landmark fallback on Python 3.13+ (returns no landmarks unless explicitly forced). Set `JARVIS_FORCE_VISION_LANDMARKS=1` to opt in to landmark extraction on those runtimes.

Run an end-to-end local self-test (listener + ingest + automation):

```bash
python3 -m jarvis vision-self-test
```

Validate specific ingest modes:

```bash
python3 -m jarvis vision-self-test json
python3 -m jarvis vision-self-test multipart
python3 -m jarvis vision-self-test binary
python3 -m jarvis vision-self-test all
```

Force signature validation for the self-test even when `JARVIS_VISION_SECRET` is unset:

```bash
python3 -m jarvis vision-self-test json --with-secret
```

Include detailed diagnostics in output (timings + processed items):

```bash
python3 -m jarvis vision-self-test multipart --with-secret --report
```

Run all ingest modes in one combined report:

```bash
python3 -m jarvis vision-self-test all --with-secret --report
```

Stop early on first failure while running all modes:

```bash
python3 -m jarvis vision-self-test all --with-secret --report --fail-fast
```

Limit all-mode to the first N ingest paths (for faster smoke checks):

```bash
python3 -m jarvis vision-self-test all --max-modes 2 --report
```

Select explicit ingest modes (instead of prefix capping):

```bash
python3 -m jarvis vision-self-test all --modes binary,json --report
```

Write output to a JSON artifact file (useful for CI):

```bash
python3 -m jarvis vision-self-test all --modes json,binary --report --output-file .artifacts/vision-self-test.json
```

Append one JSON record per run (JSONL history):

```bash
python3 -m jarvis vision-self-test json --output-file .artifacts/vision-self-test.jsonl --output-format jsonl
python3 -m jarvis vision-self-test binary --output-file .artifacts/vision-self-test.jsonl --output-format jsonl
```

Summarize that JSONL history:

```bash
python3 -m jarvis vision-self-test-summary .artifacts/vision-self-test.jsonl
python3 -m jarvis vision-self-test-summary .artifacts/vision-self-test.jsonl --mode json
python3 -m jarvis vision-self-test-summary .artifacts/vision-self-test.jsonl --last 20
python3 -m jarvis vision-self-test-summary .artifacts/vision-self-test.jsonl --percentiles 50,90,95,99
python3 -m jarvis vision-self-test-summary .artifacts/vision-self-test.jsonl --strict
python3 -m jarvis vision-self-test-summary .artifacts/vision-self-test.jsonl --max-invalid-lines 2
python3 -m jarvis vision-self-test-summary .artifacts/vision-self-test.jsonl --ema-alpha 0.6
python3 -m jarvis vision-self-test-summary .artifacts/vision-self-test.jsonl --last 100 --max-invalid-line-rate-delta 0.1
python3 -m jarvis vision-self-test-summary .artifacts/vision-self-test.jsonl --max-invalid-line-rate-ema 0.2
```

The summary includes pass/fail counts, mode counts, average timings, and timing percentiles (default `p50`/`p95`, configurable via `--percentiles`) for `http_post`, `drain_monitor_queue`, and `process_automation` when timing data exists.
It also includes `scanned_lines`, `invalid_lines`, `invalid_line_rate`, `invalid_line_rate_ema` (configurable via `--ema-alpha`, default `0.3`), and last-window trend fields (`invalid_line_rate_previous_window`, `invalid_line_rate_delta`) for parser quality monitoring.

Use `--strict` in CI to fail fast when any invalid JSONL lines are present.
Use `--max-invalid-lines N` to allow a bounded number of invalid lines before failing.
Use `--max-invalid-line-rate-delta X` to fail CI when the invalid-line rate spikes more than `X` between the previous and current windows (e.g. `0.1` = 10 percentage-point jump). The gate is skipped when there is no previous window to compare against.
Use `--max-invalid-line-rate-ema X` to fail CI when the smoothed EMA of the invalid-line rate exceeds `X` (0.0–1.0). Unlike the delta gate, this fires even with a single window — it reflects sustained degradation rather than a sudden spike.

All five CI gate parameters can also be set via environment variables, which act as project-wide defaults that CLI flags override:

| Env var | CLI flag equivalent | Type |
|---|---|---|
| `JARVIS_SUMMARY_STRICT` | `--strict` | `1`/`true`/`yes` |
| `JARVIS_MAX_INVALID_LINES` | `--max-invalid-lines N` | integer |
| `JARVIS_EMA_ALPHA` | `--ema-alpha A` | float (0,1] |
| `JARVIS_MAX_INVALID_LINE_RATE_DELTA` | `--max-invalid-line-rate-delta X` | float ≥ 0 |
| `JARVIS_MAX_INVALID_LINE_RATE_EMA` | `--max-invalid-line-rate-ema X` | float 0–1 |

If `JARVIS_VISION_SECRET` is set, the template includes `X-Jarvis-Signature`.

The vision listener also accepts direct image uploads, so you can skip manual
base64 conversion in iPhone Shortcuts:

```bash
curl -X POST http://127.0.0.1:9021/frame \
    -H "X-Device: iphone_camera" \
    -H "X-Frame-Id: raw-1" \
    -H "X-Labels: person,door" \
    -H "X-Text: front door" \
    -H "Content-Type: image/jpeg" \
    --data-binary @frame.jpg
```

It also accepts multipart form uploads (`multipart/form-data`) with an image
field plus optional metadata fields (`device`, `frame_id`, `labels`, `text`).

Post a frame (example JSON):

```bash
curl -X POST http://127.0.0.1:9021/frame \
    -H "Content-Type: application/json" \
    -d '{
        "device": "rayban_meta",
        "frame_id": "frame-001",
        "labels": ["person", "door"],
        "text": "Front door",
        "image_base64": "aGVsbG8="
    }'
```

Then process events and inspect resulting approval actions:

```bash
python3 -m jarvis events-process 20
python3 -m jarvis events-actions 20 vision_frame
```

Approval API endpoints:
- `GET /` (minimal web UI)
- `GET /health`
    - Includes readiness hints for operational use:
        - `chat.configured` / `chat.accounts`
        - `ai.ready` (Anthropic key present)
- `GET /approvals/pending?limit=100`
- `POST /approvals/{id}/approve` with JSON `{"reason":"..."}`
- `POST /approvals/{id}/reject` with JSON `{"reason":"..."}`
- `POST /approvals/dispatch` with JSON `{"limit":100}`
- `POST /chat/inbound` with JSON `{"account_id":"...","token":"...","source":"ios_shortcuts","text":"..."}`
    - Emits a `chat_message` event and, when available, returns an immediate `reply` from Jarvis.
- `POST /chat/twilio?account_id=...&token=...` with form body fields from Twilio (`From`, `To`, `Body`, `MessageSid`)
    - Accepts inbound SMS-style webhook payloads and emits `chat_message` events (`source=chat_twilio_sms`).

Quick text-chat smoke test:

```bash
export JARVIS_CHAT_ACCOUNT_ID=nick
export JARVIS_CHAT_AUTH_TOKEN=chat-secret
python3 -m jarvis approvals-api 127.0.0.1 8083
```

In another terminal:

```bash
curl -sS -X POST http://127.0.0.1:8083/chat/inbound \
    -H "Content-Type: application/json" \
    -d '{"account_id":"nick","token":"chat-secret","source":"ios_shortcuts","text":"hey jarvis, help me plan tomorrow"}'
```

Expected response includes `{"status":"accepted", ...}` and may include `reply` when the chat brain is available.

Twilio webhook URL example:

```text
https://YOUR_PUBLIC_HOST/chat/twilio?account_id=nick&token=chat-secret
```

Configure that URL as the inbound Messaging webhook in Twilio Console. Jarvis parses `Body` text,
stores it in the event bus, and returns JSON with `status` and `event_id`.

Stale pending approvals are auto-denied when you run approval commands, based on
`JARVIS_APPROVALS_TTL_SECONDS`.

Dispatch safety controls:
- `JARVIS_APPROVALS_DISPATCH_COOLDOWN_SECONDS` pauses dispatches for a cooldown
    period after the most recent dispatch.
- `JARVIS_APPROVALS_DISPATCH_MAX_PER_RUN` limits how many approved items are
    processed in one dispatch run.
- `JARVIS_APPROVALS_DISPATCH_COOLDOWN_BY_KIND` applies cooldown per approval
    kind. Format: `kind:seconds,kind:seconds` (example:
    `message_send:60,trade:300`).

## Files this creates

- `~/jarvis-notes/` — your markdown vault (override with `JARVIS_NOTES_DIR`)
- `~/.jarvis/audit.db` — append-only audit log (override with `JARVIS_AUDIT_DB`)
- `~/.jarvis/approvals.db` — approval queue store (override with `JARVIS_APPROVAL_DB`)
- `~/.jarvis/message-outbox.jsonl` — dry-run outbound messages
- `~/.jarvis/event-bus.db` — perception event bus database
- `~/.jarvis/dropzone/` — files watched by filesystem monitor
- `policies.yaml` — hard policy rules (already in this repo, edit freely)
    - default critical smart-home entities are gated by policy patterns:
        `lock.*`, `alarm_control_panel.*`, `cover.garage*`, `switch.oven*`, `climate.oven*`

## Verifying the audit log isn't tampered with

Quick CLI check:

```bash
python3 -m jarvis audit-verify
python3 -m jarvis audit-correlation <correlation_id> [limit|--limit <n>] [--kind <event_kind>]
```

### CLI JSON Error Code Reference

Jarvis CLI argument/parser failures return structured JSON with `ok: false` and
an `error` code. Use this reference for automation and alerting.

| Error code | Typical commands | Meaning |
|---|---|---|
| `unknown_argument` | `audit-correlation`, `events-actions`, `vision-self-test-summary` | Unsupported flag/token was provided. |
| `missing_limit_value` | `audit-correlation` | `--limit` or `--limit=` missing a numeric value. |
| `invalid_limit_value` | `audit-correlation` | Limit value could not be parsed as integer. |
| `conflicting_limit_filters` | `audit-correlation` | Multiple limit inputs disagree (positional/flag or repeated flags). |
| `missing_kind_value` | `audit-correlation`, `events-actions` | `--kind` or `--kind=` missing a value. |
| `conflicting_kind_filters` | `audit-correlation`, `events-actions` | Multiple kind filters disagree. |
| `missing_correlation_id_value` | `events-actions` | `--correlation-id` or `--correlation-id=` missing a value. |
| `conflicting_correlation_id_filters` | `events-actions` | Repeated correlation-id filters disagree. |
| `missing_image_arg` | `vision-analyze` | No input image/file/base64 argument supplied. |
| `image_file_not_found` | `vision-analyze` | Input file path does not exist. |
| `missing_max_colors_value` | `vision-analyze` | `--max-colors` or `--max-colors=` missing a value. |
| `invalid_max_colors_value` | `vision-analyze` | `--max-colors` value is not a valid integer. |
| `missing_input_file` | `vision-self-test-summary` | Required summary input path is missing. |
| `input_file_not_found` | `vision-self-test-summary` | Summary input path does not exist. |
| `missing_mode_filter_value` | `vision-self-test-summary` | `--mode` or `--mode=` missing a value. |
| `invalid_mode_filter` | `vision-self-test-summary` | Unsupported `--mode` value. |
| `missing_last_value` | `vision-self-test-summary` | `--last` or `--last=` missing a value. |
| `invalid_last_value` | `vision-self-test-summary` | `--last` value is invalid/out of allowed range. |
| `missing_percentiles_value` | `vision-self-test-summary` | `--percentiles` or `--percentiles=` missing a value. |
| `invalid_percentiles_value` | `vision-self-test-summary` | Percentiles are malformed, non-numeric, or out of range. |
| `missing_max_invalid_lines_value` | `vision-self-test-summary` | `--max-invalid-lines` or equals form missing a value. |
| `invalid_max_invalid_lines_value` | `vision-self-test-summary` | Max invalid lines is not a valid integer/range. |
| `missing_ema_alpha_value` | `vision-self-test-summary` | `--ema-alpha` or equals form missing a value. |
| `invalid_ema_alpha_value` | `vision-self-test-summary` | EMA alpha is non-numeric or out of allowed range. |
| `missing_max_invalid_line_rate_delta_value` | `vision-self-test-summary` | Delta gate flag missing a value. |
| `invalid_max_invalid_line_rate_delta_value` | `vision-self-test-summary` | Delta gate value is non-numeric or invalid range. |
| `missing_max_invalid_line_rate_ema_value` | `vision-self-test-summary` | EMA gate flag missing a value. |
| `invalid_max_invalid_line_rate_ema_value` | `vision-self-test-summary` | EMA gate value is non-numeric or invalid range. |
| `missing_max_modes_value` | `vision-self-test` | `--max-modes` or equals form missing a value. |
| `invalid_max_modes_value` | `vision-self-test` | `--max-modes` value is invalid (must be positive integer). |
| `missing_modes_value` | `vision-self-test` | `--modes` or `--modes=` missing CSV values. |
| `invalid_modes_value` | `vision-self-test` | `--modes` contains unsupported mode values. |
| `missing_output_file_value` | `vision-self-test` | `--output-file` or equals form missing a path. |
| `missing_output_format_value` | `vision-self-test` | `--output-format` or equals form missing a value. |
| `invalid_mode` | `vision-self-test` | Positional self-test mode is unsupported. |
| `invalid_output_format` | `vision-self-test` | Output format is unsupported (expected json/jsonl). |
| `modes_requires_all_mode` | `vision-self-test` | `--modes` used without positional mode `all`. |

Additional structured runtime/quality-gate errors used by
`vision-self-test-summary`:

- `invalid_history_lines`
- `invalid_line_rate_delta_exceeded`
- `invalid_line_rate_ema_exceeded`

### CLI Parser Behavior Guarantees

The CLI parser follows these invariants so automation can rely on predictable behavior:

- Repeated same-value flags are idempotent: repeated equivalent filters are accepted.
    - Example: `--limit 5 --limit=5`, `--kind x --kind=x`.
- Conflicting repeated filters fail fast with structured errors.
    - Example: different `--kind` values return `conflicting_kind_filters`.
    - Example: different `--correlation-id` values return `conflicting_correlation_id_filters`.
    - Example: different limit sources return `conflicting_limit_filters`.
- Empty equals-style flags are treated as missing values.
    - Example: `--kind=` -> `missing_kind_value`.
    - Example: `--limit=` -> `invalid_limit_value` for numeric flags.
    - Example: `--max-colors=` -> `missing_max_colors_value`.
- Unknown tokens are rejected explicitly.
    - Example: unsupported flags return `unknown_argument`.
- Numeric limit parsing is standardized across event/audit commands.
    - Invalid numbers return `invalid_limit_value`.
    - Event command limits (`events-list`, `events-process`, `events-actions`) require positive integers.

Python check:

```python
from pathlib import Path
from jarvis.audit import AuditLog
log = AuditLog(Path("~/.jarvis/audit.db").expanduser())
print(log.verify())   # True if every row's hash matches the chain
```

If `verify()` returns `False`, somebody (or some bug) modified a row directly in SQLite — every later row's hash becomes invalid.

## Structured Logging and Observability

Jarvis logs all events to both console and the audit log:

```python
from jarvis.logging_util import setup_logging, get_logger

# Initialize logging (called automatically in CLI commands)
setup_logging()

# Get a logger
logger = get_logger("my_module")

# Log messages go to both console and audit log
logger.info("Approval requested: 123-abc")
logger.warning("This approval is stale")
```

Logs are automatically:
- Written to console for immediate feedback (INFO level and above)
- Written to audit log for complete tracing (DEBUG level and above)
- Included in the hash-chained audit trail (tamper-evident)

Query recent logs:

```python
from jarvis.audit import AuditLog
from pathlib import Path

log = AuditLog(Path("~/.jarvis/audit.db").expanduser())

# Get last 50 INFO logs
info_logs = log.recent(limit=50, kind="log_info")
for event in info_logs:
    print(event["payload"]["message"])
```

## Quick Start: Approval Workflow

Test the approval queue end-to-end:

```bash
# Terminal 1: Start the approvals API server
python3 -m jarvis approvals-api 127.0.0.1 8083

# Terminal 2: Create demo pending approvals
python3 -m jarvis approvals-seed 3

# In your browser, open:
# http://127.0.0.1:8083/

# Use the web UI to:
# 1. Refresh the pending list (shows 3 demo items)
# 2. Click Approve or Reject on each
# 3. Click "Dispatch Approved" to send approved items to outbox

# Check the outbox:
tail -2 ~/.jarvis/message-outbox.jsonl
```

Or use the CLI directly:

```bash
# List pending
python3 -m jarvis approvals-list

# Approve one by ID
python3 -m jarvis approvals-approve <id> "looks good"

# Dispatch all approved items
python3 -m jarvis approvals-dispatch
```

## Tests

```bash
pip install pytest
pytest tests/

# full validation (lint + full tests + audit chain verify)
make verify

# install and run git pre-commit hooks (ruff + black + quick pytest)
pip install pre-commit
pre-commit install
pre-commit run --all-files
```

Tests cover the audit log (append, verify, tamper-detection) and the policy engine (blocked tools, blocked domains, path traversal). They don't require an API key.

## Layout

```
jarvis/
├── README.md                this file
├── requirements.txt
├── .env.example
├── policies.yaml            hard policy rules
├── jarvis/
│   ├── __init__.py
│   ├── __main__.py          python3 -m jarvis
│   ├── cli.py               REPL
│   ├── config.py            env-driven config
│   ├── audit.py             hash-chained SQLite log
│   ├── approval.py          approval queue store
│   ├── approval_service.py  approval boundary service
│   ├── approval_api.py      approval HTTP API surface
│   ├── memory.py            in-process conversation
│   ├── policy.py            pre-flight tool checks
│   ├── brain.py             agent loop with enforced dispatch preflight
│   ├── runtime/             turn orchestration scaffold
│   │   └── explicit stages: perceive -> plan -> preflight -> dispatch -> observe
│   │   └── typed tool contract: name, schema, handler, tier
│   │   └── event envelope: source, timestamp, correlation_id, payload
│   │   └── structured dispatch errors: policy-denied, tool-not-found, tool-bad-args, tool-failure
│   └── tools/               registry with open/gated metadata
│       ├── __init__.py      registry
│       ├── web_search.py
│       ├── web_fetch.py
│       ├── notes.py
│       ├── recall.py
│       ├── gated.py
│       └── message_send.py
└── tests/
    ├── test_audit.py
    └── test_policy.py
```

## Extending

Adding a tool is three steps:

1. Write a `Tool` (handler + JSON schema) in `jarvis/tools/your_tool.py`.
2. Register it in `jarvis/cli.py:build_brain()`.
3. If it does anything the policy engine should restrict, add a check in `jarvis/policy.py`.

When you're ready for phase 2, voice slots in by replacing `cli.py` with a wake-word loop that pipes Whisper transcripts into `brain.turn()`; the brain itself doesn't change.

See `docs/runbooks/wake-word-integration-evaluation.md` for the evaluated integration path and implementation sequence.
