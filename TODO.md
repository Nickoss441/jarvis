# Jarvis Complete Scaffolding TODO

Use this as the build-order checklist from architecture to production-ready scaffold.

## Current Sprint TODOs

- [x] P0: Add tests for repeated same-value flags to document accepted idempotent behavior.
- [x] P0: Add duplicate/empty equals validation parity for remaining equals-style CLI flags.
- [x] P0: Add test coverage for edge-case limit bounds (`0`, negative, very large values).
- [x] P1: Add JSON error code reference table in README for all CLI parser errors.
- [x] P1: Add smoke test that exercises `audit-correlation` and `events-actions` with mixed flag styles.
- [x] P2: Add CLI parser helper utilities to reduce duplicated argument-walking logic.
- [x] P2: Add `make verify` command to run lint + full tests + audit verify.

## Next Sprint TODOs

- [x] P0: Add shared numeric flag parsing helper with optional min/max constraints and standard error mapping.
- [x] P0: Apply numeric helper to `audit-correlation --limit`, `events-actions <limit>`, `events-list <limit>`, and `events-process <limit>`.
- [x] P0: Add parser tests for zero/negative/invalid limits on `events-actions`, `events-list`, and `events-process`.
- [x] P1: Add mixed-style smoke test for vision CLIs (`vision-analyze`, `vision-self-test`, `vision-self-test-summary`).
- [x] P1: Add README section with parser behavior guarantees (idempotent repeated flags, conflicting filters, empty equals handling).
- [x] P2: Add lightweight benchmark test to track parser path latency across common CLI commands.

## Fundamental Next (Do This First)

- [x] Create `jarvis/approval_service.py` as the single approval boundary API over `ApprovalStore`.
- [x] Move approval command logic out of `__main__.py` into the service layer.
- [x] Add audit events for approval lifecycle: `approval_requested`, `approval_expired`, `approval_approved`, `approval_rejected`, `approval_dispatched`.
- [x] Add correlation IDs from tool request -> approval -> dispatch.
- [x] Rewire `message_send` to use approval service methods only (no direct store access from CLI/tool wiring).
- [x] Add service-level tests for approve/reject/expire/dispatch behavior.
- [x] Keep CLI commands as thin wrappers over the service (`approvals-list`, `approvals-approve`, `approvals-reject`, `approvals-dispatch`).

## 0) Project Foundations

- [x] Confirm deployment target: laptop, home server, or VPS.
- [x] Decide voice stack for v1: local (faster-whisper + Piper) or cloud (Deepgram + ElevenLabs).
- [x] Decide push/approval channel: ntfy, Pushover, Twilio SMS, or app-only.
- [x] Decide paper-trading broker: FXOpen, Alpaca, or IBKR.
- [x] Define critical smart-home entities (locks, alarm, garage, oven) for gated policy.
- [x] Freeze outbound call disclosure template.
- [x] Add `Makefile` tasks: `setup`, `run`, `test`, `lint`, `format`, `verify-audit`.
- [x] Add `.env.example` values for all planned integrations (commented where not yet used).
- [x] Add pre-commit hooks (ruff/black/pytest quick checks).

## 1) Core Runtime Scaffold

 - [x] Create `jarvis/runtime/` package for agent loop orchestration.
- [x] Split brain loop into explicit stages: perceive -> plan -> preflight -> dispatch -> observe.
- [x] Define typed tool interface contract (name, schema, handler, tier).
- [x] Add tool registry with open/gated metadata.
- [x] Add unified event envelope model (source, timestamp, correlation_id, payload).
- [x] Add deterministic policy preflight hook before every tool call.
- [x] Add structured error types for policy-denied, tool-timeout, tool-failure.
- [x] Add retry policy with max attempts for transient tool failures.

## 2) Sprint: Config, Policy, and Observability Hardening

### Config validation
- [x] Add `Config.validate()` method that raises `ValueError` for missing required keys per enabled phase flag.
- [x] Add `Config.phase_enabled(phase: str) -> bool` helper and tests covering all six phase flags.
- [x] Add env-var presence check for `ANTHROPIC_API_KEY` at startup with a clear human-readable error (not a stack trace).
- [x] Expand `.env.example` with per-flag "what breaks without this" comments for all phase flags.

### Policy hardening
- [x] Add configurable quiet-hours tool restriction to `Policy` (`no_call_hours_start`, `no_call_hours_end`) with tests.
- [x] Add per-tool rate-limit rules to `Policy` (max N calls per hour per tool kind, mirrors event throttle pattern) with tests.
- [x] Add `policies.yaml` schema validator on `Policy.from_file()` that warns on unknown keys and fails on invalid types.
- [x] Add `jarvis stop` kill-switch CLI command that writes a `~/.jarvis/stopped` sentinel file and `jarvis resume` to remove it.

### Audit / observability
- [x] Add PII redaction helper `redact_payload()` in `jarvis/audit.py` that strips keys matching patterns (`api_key`, `password`, `token`, `card_*`, `secret`).
- [x] Add `audit-export` CLI command that dumps the full chain as JSONL to stdout.
- [x] Add `audit-stats` CLI command (event counts by kind, oldest/newest ts, chain length).
- [x] Mark as done: `audit verify` CLI, `audit-correlation` CLI, correlation IDs across perception/tools/approvals, event types for approvals/gated proposals.

### Perception resilience
- [x] Add per-monitor restart/backoff state to `MonitorRunner` (track consecutive failures, exponential backoff cap).
- [x] Add `jarvis monitors-status` CLI command showing each monitor's last-run timestamp and cumulative event count.
- [x] Add event-bus healthcheck helper `EventBus.healthcheck() -> bool` (checks DB writable and not locked).

### Testing gaps
- [x] Add contract test: every tool registered in the default registry must have a schema with valid JSON Schema `type: object`.
- [x] Add chaos test: mock tool handler that raises `RuntimeError` — assert dispatch returns `tool-failure` typed error.
- [x] Add audit tamper test: mutate one payload row directly in SQLite, assert `verify()` returns `False`.

## 2b) Sprint: Policy Rules Engine Expansion

### Quiet-hours enforcement
- [x] Add `QuietHoursRule` dataclass (`start_hour: int`, `end_hour: int`, `blocked_tools: list[str]`) to `jarvis/policy.py`.
- [x] Wire `QuietHoursRule` into `Policy.check_tool` — deny matched tools outside allowed hours with `"quiet hours"` reason.
- [x] Load quiet-hours config from `policies.yaml` `quiet_hours:` key.
- [x] Add 5 tests: tool blocked inside quiet window, allowed outside, boundary exact-hour edge cases, empty blocked_tools list.

### Per-tool rate limits
- [x] Add `RateLimitRule` dataclass (`tool_pattern: str`, `max_calls: int`, `window_seconds: int`) to `jarvis/policy.py`.
- [x] Add `PolicyRateLimiter` class (in-memory `dict[str, deque[float]]`) that `Policy.check_tool` consults before dispatching.
- [x] Load rate limit config from `policies.yaml` `rate_limits:` key.
- [x] Add tests: first N calls pass, N+1 is denied, window expiry resets the counter.
- [x] Add `policy-rate-limited` as a new `RuntimeErrorKind` in `jarvis/runtime/errors.py`.

### policies.yaml schema validation
- [x] Define allowed top-level keys in a `POLICY_SCHEMA` dict in `policy.py` (`blocked_tools`, `phase_gates`, `domain_blocks`, `notes_path_block`, `critical_smart_home_patterns`, `quiet_hours`, `rate_limits`).
- [x] In `Policy.from_file()` check for unknown keys and `raise ValueError` listing them.
- [x] Add tests: valid file passes, file with unknown key raises, file with wrong type raises.

## 2c) Sprint: Audit Hardening

### PII redaction
- [x] Add `_REDACT_PATTERNS: frozenset[str]` constant in `jarvis/audit.py` covering `api_key`, `password`, `token`, `secret`, `card_number`, `cvv`, `ssn`.
- [x] Add `redact_payload(payload: dict) -> dict` pure function (recursive, replaces matched values with `"[REDACTED]"`).
- [x] Call `redact_payload` inside `AuditLog.append()` before writing.
- [x] Add 6 unit tests: top-level key, nested key, list-of-dicts, unknown key untouched, `None` value, already-redacted value is idempotent.

### Audit export and stats
- [x] Add `AuditLog.export_jsonl(out: IO[str]) -> int` method that streams every row as a JSONL line and returns row count.
- [x] Add `audit-export` CLI command in `jarvis/__main__.py` that calls `export_jsonl(sys.stdout)`.
- [x] Add `AuditLog.stats() -> dict` returning `{kind: count}` map, plus `oldest_ts`, `newest_ts`, `chain_length`.
- [x] Add `audit-stats` CLI command that pretty-prints the stats dict.
- [x] Add tests for `export_jsonl` (roundtrip parse check) and `stats` (correct counts and timestamps).

### Audit tamper detection test
- [x] Add `test_audit_verify_detects_tampered_payload` in `tests/test_audit.py`: write 3 rows, UPDATE one payload directly via sqlite3, assert `verify()` returns `False`.
- [x] Add `test_audit_verify_detects_tampered_hash` in `tests/test_audit.py`: UPDATE one `prev_hash` directly, assert `verify()` returns `False`.

## 3) Config, Secrets, and Environment (deferred / phase-gated)

- [x] Expand config model for voice, home-assistant, and telephony modules when those phases activate.
- [x] Add secret-provider abstraction (env, keychain, 1Password/Bitwarden adapter) — needed before live trading or telephony.
- [x] Ensure secrets are fetched at call time, never logged (audit PII redaction from Sprint 2 is the first step).

## 4) Audit, Logging, and Observability (deferred)

- [x] Append-only SQLite hash-chain audit log.
- [x] `audit verify` CLI command.
- [x] `audit-correlation` CLI command.
- [x] Correlation IDs across perception, reasoning, tools, and approvals.
- [x] Healthcheck endpoint for monitors and event bus (partial — `monitors-status` CLI above covers this).

## 5) Perception Layer Scaffold

- [x] Add `jarvis/perception/voice/` module scaffold (wake-word, STT, TTS adapters) — Phase 2.
- [x] `jarvis/perception/monitors/` — Calendar, RSS, Webhook, Vision, Filesystem monitors all shipped.
- [x] SQLite-backed event bus.
- [x] Monitor supervisor with per-monitor restart/backoff (scheduled in Sprint 2 above).
- [x] Add `jarvis/perception/chat/` iOS-Shortcuts / bot adapter scaffold — Phase 2.

## 5) Tooling Layer Scaffold

### Open tools

- [x] Keep/upgrade `web_search`, `web_fetch`, `notes`, `recall`.
- [x] Add `calendar_read` scaffold.
- [x] Add `mail_draft` scaffold (store draft locally only).
- [x] Add `home_assistant` read and non-critical write scaffold.

### Gated tools

- [x] Add `message_send` scaffold (approval required).
- [x] Add `call_phone` scaffold (approval + disclosure).
- [x] Add `payments` scaffold (approval + policy checks + budget impact).
- [x] Add `trade` scaffold (paper mode first).
- [x] Add `shell`/`file_write` scaffold for sandbox-only operations.

## 6) Approval Gate Scaffold

- [x] Create `jarvis/approval/` service with pending approval queue.
- [x] Define approval payload schema: action, reason, budget impact, TTL, risk tier.
- [x] Add approve/reject/edit endpoints.
- [x] Add push notifier adapters (ntfy first, others behind interface).
- [x] Add minimal approval web UI (localhost) with one-tap actions.
- [x] Enforce tier-based cooldown rules (0s/5s).
- [x] Expire stale approvals and auto-deny on TTL timeout.

## 7) Security and Governance Scaffold

- [x] Convert `policies.yaml` into explicit policy-as-code schema with validation.
- [x] Add domain allow/deny lists and path traversal guards globally.
- [x] Add schedule-based restrictions (quiet hours, no weekend spend, etc.).
- [x] Add rate limits for payments and message sends.
- [x] Add kill-switch command `jarvis stop` to pause monitors and gated calls.
- [x] Add sandbox profile definitions for shell/web fetch execution.
- [x] Add security test fixtures for prompt-injection and unsafe tool arguments.

## 8) Payments Scaffold (Phase 5)

- [x] Add virtual-card budget config (`monthly_cap`, `tx_limit`, allowed MCCs).
- [x] Add internal budget ledger table and monthly rollover logic.
- [x] Add payment proposal builder with merchant + line-item validation.
- [x] Add reconciliation webhook endpoint (Stripe/card provider).
- [x] Alert on unexpected charges (no matching proposal in audit).
- [x] Add spend-tier behavior tests (`0-10`, `10-100`, `100+`).

## 9) Telephony Scaffold (Phase 6)

- [x] Add Twilio outbound call adapter.
- [x] Add mandatory first-line disclosure injection.
- [x] Add call recording + transcript persistence to audit.
- [x] Add branch for "human requested" graceful handoff.
- [x] Add call-time window policies and contact allowlist checks.

## 10) Trading Scaffold (Phase 6+)

- [x] Add paper trading adapter first (no live by default).
- [x] Add proposal schema with instrument/side/size/SL/TP/rationale.
- [x] Add hard position-size cap policy (for example max 2% equity).
- [x] Add live-mode gate requiring per-trade confirm and cooldown.
- [x] Add daily drawdown pause policy and reset logic.
- [x] Add trade replay report generation from audit trail.

## 11) Testing and Quality Gates

- [x] Add unit tests for policy preflight for every gated tool.
- [x] Add integration tests for approval flow and TTL expiry.
- [x] Add contract tests for each tool schema and handler output.
- [x] Add audit tamper tests for all new event types.
- [x] Add end-to-end simulation: voice/request -> approvals -> tool action -> audit.
- [x] Add chaos tests for tool timeout, webhook delay, and duplicate events.

## 12) Developer Experience and Docs

- [x] Update `README.md` with phased capability matrix and quickstart per phase.
- [x] Add `docs/` runbooks: approvals, kill-switch, incident response, key rotation.
- [x] Add architecture decision records (ADRs) for major tradeoffs.
- [x] Add local demo scripts for each gated tool in dry-run mode.
- [x] Add sample `policies.yaml` templates: strict, balanced, permissive.

## 13) Milestone Exit Criteria

- [x] Phase 1 complete: chat runtime + open tools + audit + policy tests passing.
- [x] Phase 2 complete: voice round-trip stable with acceptable latency.
- [x] Phase 3 complete: smart-home non-critical controls with policy enforcement.
- [x] Phase 4 complete: approval UI + first gated tool fully audited.
- [x] Phase 5 complete: payment caps, webhooks, reconciliation, alerts validated.
- [x] Phase 6 complete: telephony disclosure flow + paper trading stable.
- [ ] Live trading unlock only after documented paper-performance review.

## Immediate Next 7 Tasks (Recommended)

- [x] Implement feature flags and expanded config model.
- [x] Create approval service skeleton (`jarvis/approval/`).
- [x] Introduce event envelope + correlation IDs across runtime.
- [x] Add gated tool metadata to registry and enforce preflight centrally.
- [x] Add `audit verify` CLI command.
- [x] Scaffold `calendar_read` and `mail_draft` tools.
- [x] Implement approval TTL + auto-deny for stale pending items, with tests.
