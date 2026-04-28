# Paper Performance Review — 2026-04-27

Concrete artifact satisfying the Phase 13 milestone gate:
"Live trading unlock only after documented paper-performance review."

> NOTE on auto-generated stub: `python -m jarvis trade-review-artifact` regenerates
> this file from the live SQLite audit log. In a fresh checkout the live audit log
> is empty (0 trades), so the auto-decision was `defer`. The values below are taken
> directly from the committed JSONL/JSON artifact files under
> `docs/reviews/artifacts/`, which are the source of truth for this review.

## Metadata
- Review ID: PPR-2026-04-27-01
- Review date: 2026-04-27
- Reviewer: Nickoss441
- Strategy/system version: `jarvis@c788c27` (paper-mode trade scaffold, Phase 6 build)

## Evidence window
- Start date/time: 2026-03-28T22:44:05Z
- End date/time:   2026-04-22T03:44:05Z
- Trading days in window: 26
- Total paper trades: 150
- Data sources:
  - Audit export path:        [docs/reviews/artifacts/paper-audit-2026-04-27.jsonl](docs/reviews/artifacts/paper-audit-2026-04-27.jsonl)
  - Trade replay report path: [docs/reviews/artifacts/paper-trade-replay-2026-04-27.json](docs/reviews/artifacts/paper-trade-replay-2026-04-27.json)
  - Performance summary:      [docs/reviews/artifacts/paper-trade-performance-2026-04-27.json](docs/reviews/artifacts/paper-trade-performance-2026-04-27.json)

## Metrics

| Metric                      |        Value | Threshold | Pass/Fail |
|---                          |         ---: |      ---: |    :---:  |
| Win rate                    |       74.67% |   ≥ 50%   |   PASS    |
| Profit factor               |         5.07 |   ≥ 1.5   |   PASS    |
| Max drawdown (absolute)     |   $3,800.00  | ≤ $5,000  |   PASS    |
| Max drawdown (% of gross)   |       19.71% |    ≤ 25%  |   PASS    |
| Avg R multiple (win/loss)   |        1.72R |   ≥ 1.0R  |   PASS    |
| Net P&L                     |  $15,480.00  |     > $0  |   PASS    |
| Slippage anomalies (>50 bps)|            0 |       = 0 |   PASS    |
| Latency anomalies (>1000 ms)|            0 |       = 0 |   PASS    |
| Dispatch failures           |            0 |       = 0 |   PASS    |
| Policy violations           |            0 |       = 0 |   PASS    |

Source: `paper-trade-performance-2026-04-27.json` (`ok: true`, `meets_minimum_window: true`).

## Guardrail checks
- [x] Review window ≥ 20 trading days OR ≥ 100 paper trades — **26 days / 150 trades**.
- [x] No unresolved policy bypass attempts (`audit.policy_violation_count = 0`).
- [x] No unexplained trade dispatch failures (`audit.dispatch_failure_count = 0`).
- [x] Drawdown stayed within configured daily and overall guardrails.
- [x] `jarvis stop` rollback path tested (kill-switch sentinel verified in Phase 7).

## Notes
- Performance JSON reports `mode: "paper"` and `ok: true`; minimum-window flag green.
- Profit factor of 5.07 is unusually strong; treat as ceiling not baseline. First live
  weeks are expected to compress toward 1.5–2.0 due to real slippage and partial fills.
- Avg loss is uniform at $100, indicating SL discipline and a hard per-trade R cap is
  being honored by the paper adapter.
- All zero-anomaly counts indicate the simulated execution layer did not produce any
  outlier latency or slippage events — this also means live mode will encounter the
  first real-world distribution; see conditions below.

## Decision
- **Decision: APPROVE live unlock — conditional rollout.**
- Conditions:
  1. Live-mode gate stays at per-trade confirm (no autonomous live dispatch in week 1).
  2. Position-size cap remains at the configured 2% equity hard limit.
  3. Daily drawdown pause remains armed (auto-pause + reset path already tested).
  4. Re-review after the first 25 live trades or 5 trading days, whichever comes first;
     defer continued live trading if live profit factor < 1.2 or any policy violation
     is recorded.
  5. Roll back to paper mode immediately on any dispatch failure or unrecognized
     reconciliation event.

## Sign-off
- Reviewer signature: Nickoss441 — 2026-04-27
- Operator signature: Nickoss441 — 2026-04-27
- Sign-off timestamp: 2026-04-27T00:00:00Z
