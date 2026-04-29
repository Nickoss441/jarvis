# Task List (2026-04-28)

This list is generated from the currently open backlog items in TODO.md and organized in execution order.

## 1) Blocker

- [ ] Rotate API key and run live agent E2E smoke test (REPL + vocal trigger: "respond vocally: status report")

## 2) Command Center Live Data Wiring

- [ ] Wire Bitcoin panel to real data via crypto_portfolio tool
- [ ] Wire Social Monitoring panel to monitors-status output
- [ ] Wire Oil and Gold panel to gold-price tool + market mode config
- [ ] Wire Tracking / Strategy panel to live approval + event counts (/approvals, /events)
- [ ] Replace top and bottom marquee placeholder text with audit-export tail
- [ ] Add WebSocket or SSE bridge so HUD reflects live brain Thought:/Observation: cycles

## 3) Voice and Docs

- [ ] Add docs/runbooks/voice-output.md with recognized vocal-reply trigger phrases and disable mechanism
- [ ] Cross-link voice-output runbook from README docs index

## 4) Desktop Overlay (Tauri)

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

## 5) Production Hardening

- [ ] Pick production deployment target (laptop / home server / VPS)
- [ ] Stand up live Alpaca broker connection (separate from paper)
- [ ] Configure real ntfy or Pushover push channel
- [ ] Harden remote approval channel (currently localhost-only)
- [ ] Add health and uptime monitoring for always-on server
- [ ] Implement remote access strategy (Tailscale / Cloudflare Tunnel / VPN)
- [ ] Document backup and restore procedure for audit.db and event bus DB

## Summary

- Total open tasks: 27
- Suggested first milestone: complete sections 1 and 2
- Suggested second milestone: complete section 3
- Suggested third milestone: complete sections 4 and 5
