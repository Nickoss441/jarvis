# Next 100 Tasks (2026-04-28)

Purpose: a concrete 100-item execution list for Jarvis based on the active backlog and roadmap.

## A) Immediate Unblocks (1-10)

- [ ] 1. Rotate ANTHROPIC_API_KEY in local runtime environment
- [ ] 2. Verify key is loaded by runtime config at startup
- [ ] 3. Run REPL smoke: python -m jarvis run
- [ ] 4. Trigger vocal response test phrase end-to-end
- [ ] 5. Capture E2E smoke output in docs/reports
- [ ] 6. Add one regression test for vocal-trigger routing
- [ ] 7. Add one regression test for failed key handling path
- [ ] 8. Add troubleshooting notes for 401 key failures
- [ ] 9. Confirm .env.local remains excluded from git status
- [ ] 10. Mark blocker complete in TODO.md

## B) Command Center Live Wiring (11-30)

- [ ] 11. Locate Command Center panel render code in jarvis/web/command_center
- [ ] 12. Add server endpoint for Bitcoin data snapshot
- [ ] 13. Wire endpoint to crypto_portfolio tool output
- [ ] 14. Normalize currency formatting for BTC panel
- [ ] 15. Add stale-data indicator on BTC panel
- [ ] 16. Add Social Monitoring endpoint backed by monitors-status
- [ ] 17. Compute +delta metric for social panel
- [ ] 18. Render social trend bars from live data
- [ ] 19. Add Oil and Gold endpoint in approval_api
- [ ] 20. Source gold data from gold-price tool
- [ ] 21. Source oil mode from market config
- [ ] 22. Add fallback values when market endpoint fails
- [ ] 23. Add Tracking/Strategy endpoint with approvals counts
- [ ] 24. Include pending, approved, rejected counts
- [ ] 25. Include event throughput metric from event bus
- [ ] 26. Replace top marquee placeholders with audit-export tail
- [ ] 27. Replace bottom marquee placeholders with system telemetry
- [ ] 28. Add SSE endpoint for HUD live updates
- [ ] 29. Subscribe HUD panels to SSE stream updates
- [ ] 30. Add reconnect/backoff behavior for dropped SSE connection

## C) HUD Reliability and UX (31-40)

- [ ] 31. Add API timeout handling for every HUD data fetch
- [ ] 32. Show panel-level loading state on first paint
- [ ] 33. Show panel-level degraded state on endpoint errors
- [ ] 34. Add mobile-safe layout behavior under 900px width
- [ ] 35. Validate desktop layout at 100 percent and 125 percent scaling
- [ ] 36. Validate ultrawide layout clipping behavior
- [ ] 37. Add tests for HUD JSON endpoint schemas
- [ ] 38. Add smoke test for /hud/cc route serving
- [ ] 39. Add smoke test for /hud/react route serving
- [ ] 40. Document HUD data contract in docs/runbooks

## D) Voice and Docs (41-50)

- [ ] 41. Create docs/runbooks/voice-output.md
- [ ] 42. Document all recognized vocal trigger phrases
- [ ] 43. Document temporary disable method for vocal output
- [ ] 44. Document permanent disable configuration path
- [ ] 45. Add troubleshooting section for missing audio output
- [ ] 46. Add troubleshooting section for false-positive wake triggers
- [ ] 47. Cross-link voice runbook from README docs index
- [ ] 48. Cross-link voice runbook from QUICKSTART.md
- [ ] 49. Add test for voice disable flag behavior
- [ ] 50. Add test for fallback to text-only response mode

## E) Desktop Overlay (Tauri) (51-72)

- [ ] 51. Finalize framework choice and record ADR for Tauri decision
- [ ] 52. Scaffold src-tauri project files
- [ ] 53. Add local dev command to launch overlay shell
- [ ] 54. Configure frameless transparent always-on-top window
- [ ] 55. Point overlay webview to http://127.0.0.1:8081/hud/cc
- [ ] 56. Add startup check for HUD server availability
- [ ] 57. Add /hud/show endpoint in approval_api
- [ ] 58. Add /hud/hide endpoint in approval_api
- [ ] 59. Add auth guard or local-only restriction for show/hide endpoints
- [ ] 60. Wire global hotkey Ctrl+Shift+J on Windows
- [ ] 61. Wire global hotkey Cmd+Shift+J on macOS
- [ ] 62. Add tray icon with Show action
- [ ] 63. Add tray icon with Hide action
- [ ] 64. Add tray icon with Quit action
- [ ] 65. Implement click-through for transparent overlay regions
- [ ] 66. Add temporary click-focus mode toggle
- [ ] 67. Handle multi-display window placement
- [ ] 68. Handle display-add and display-remove events
- [ ] 69. Persist last display and position on restart
- [ ] 70. Add Windows build pipeline for signed executable
- [ ] 71. Add macOS notarization and signing pipeline
- [ ] 72. Add release packaging notes in docs/runbooks/desktop-overlay.md

## F) Approvals and Remote Operations (73-84)

- [ ] 73. Define production deployment target (laptop, server, or VPS)
- [ ] 74. Stand up production profile config file
- [ ] 75. Configure real ntfy or Pushover channel credentials
- [ ] 76. Validate approval notification delivery latency
- [ ] 77. Harden localhost-only approval UI strategy
- [ ] 78. Add remote access approach (Tailscale/Cloudflare/VPN)
- [ ] 79. Add endpoint auth and origin checks for approvals API
- [ ] 80. Add brute-force protection for approval actions
- [ ] 81. Add uptime health endpoint dashboard checks
- [ ] 82. Add alerting when approval queue stalls
- [ ] 83. Add backup procedure for approvals.db and audit.db
- [ ] 84. Add restore drill and verification procedure

## G) Trading and Risk Controls (85-92)

- [ ] 85. Stand up live Alpaca broker connection in guarded mode
- [ ] 86. Keep per-trade confirmation mandatory in live mode
- [ ] 87. Verify hard 2 percent equity position cap in policy engine
- [ ] 88. Verify daily drawdown auto-pause triggers correctly
- [ ] 89. Add live-vs-paper mode banner in CLI and HUD
- [ ] 90. Add reconciliation check for unrecognized trade events
- [ ] 91. Add live-trading rollback runbook steps
- [ ] 92. Add post-trade review checkpoint after first 25 live trades

## H) Quality Gates and Cleanup (93-100)

- [ ] 93. Run full test suite and capture failures
- [ ] 94. Fix failing tests introduced by HUD data integration
- [ ] 95. Add targeted tests for new SSE stream endpoint
- [ ] 96. Add targeted tests for /hud/show and /hud/hide endpoints
- [ ] 97. Run lint and format pass for touched files
- [ ] 98. Update TODO.md open backlog statuses
- [ ] 99. Write changelog note for completed milestone
- [ ] 100. Prepare next sprint board from remaining open work
