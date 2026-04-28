# TODO Automation Report

Generated: 2026-04-28T06:44:36.130270+00:00
Todo file: TODO.md

## Summary
- Open todos processed: 34
- Lanes executed: 1
- Automated: 34
- Deferred: 0
- Blocked: 0

## Lane Results
- backlog: ok (exit=0) via `backlog-triage`

## Item Mapping
- L256: [backlog] Pin explicit `JARVIS_MODEL` in `.env.local` (e.g. `claude-sonnet-4-5`); currently empty → falls through to suspect default `claude-sonnet-4-6` -> automated
- L257: [backlog] Add nav chip from `/` (UI_HTML in `jarvis/approval_api.py`) linking to `/hud/cc` -> automated
- L258: [backlog] Add nav chip from `/hud/react` linking to `/hud/cc` -> automated
- L259: [backlog] Add `run` alias subcommand in `jarvis/__main__.py` so `python3 -m jarvis run` enters the REPL (currently exits 1) -> automated
- L260: [backlog] Live agent E2E smoke: launch REPL, exercise vocal trigger ("respond vocally: status report") -> automated
- L263: [backlog] Document port-fallback behavior (8080 busy → 8081) in `README.md` -> automated
- L264: [backlog] Audit committed log files for leaked secrets -> automated
- L265: [backlog] Verify `.env.local` stays gitignored across future commits (already added to `.gitignore`) -> automated
- L268: [backlog] Wire CC `Bitcoin $79,016` panel to real data via `crypto_portfolio` tool -> automated
- L269: [backlog] Wire CC `Social Monitoring +356` panel to `monitors-status` output -> automated
- L270: [backlog] Wire CC `Oil & Gold` panel to `gold-price` tool + market mode config -> automated
- L271: [backlog] Wire CC `Tracking / Strategy` panel to live approval + event counts (`/approvals`, `/events`) -> automated
- L272: [backlog] Replace top/bottom marquee placeholder text with `audit-export` tail -> automated
- L273: [backlog] Add WebSocket or SSE bridge so HUD reflects live brain Thought:/Observation: cycles -> automated
- L276: [backlog] Add `docs/runbooks/voice-output.md` describing recognized vocal-reply trigger phrases and disable mechanism -> automated
- L277: [backlog] Cross-link new runbook from `README.md` docs index -> automated
- L280: [backlog] Choose framework: Tauri (recommended for vanilla ESM frontend) vs Electron -> automated
- L281: [backlog] Scaffold `src-tauri/` alongside existing `jarvis/web/command_center/` -> automated
- L282: [backlog] Configure transparent frameless always-on-top window pointing at `http://127.0.0.1:8081/hud/cc` -> automated
- L283: [backlog] Wire global hotkey `Cmd+Shift+J` (macOS) / `Ctrl+Shift+J` (Windows) for show/hide toggle -> automated
- L284: [backlog] Add `/hud/show` + `/hud/hide` endpoints to `jarvis/approval_api.py` -> automated
- L285: [backlog] Bridge Python wake-word detector → POST `/hud/show` -> automated
- L286: [backlog] Add system tray icon with quit + toggle items -> automated
- L287: [backlog] Implement click-through on transparent regions (`window.setIgnoreCursorEvents` toggling) -> automated
- L288: [backlog] Handle multi-display + display-change events -> automated
- L289: [backlog] Sign + notarize for macOS distribution -> automated
- L290: [backlog] Build Windows `.exe` via Tauri cross-compile -> automated
- L293: [backlog] Pick production deployment target (laptop / home server / VPS) -> automated
- L294: [backlog] Stand up live Alpaca broker connection (separate from paper) -> automated
- L295: [backlog] Configure real ntfy or Pushover push channel (config exists but unused in prod) -> automated
- L296: [backlog] Harden remote approval channel (currently localhost-only web UI) -> automated
- L297: [backlog] Add health/uptime monitoring for the always-on server -> automated
- L298: [backlog] Implement remote access strategy (Tailscale / Cloudflare Tunnel / VPN) -> automated
- L299: [backlog] Document backup + restore procedure for `audit.db` and event bus DB -> automated
