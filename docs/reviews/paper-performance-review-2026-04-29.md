# Paper Performance Review Record Template

Use this file to produce the concrete artifact required before live trading unlock.

## Metadata
- Review ID: paper-review-2026-04-29
- Review date: 2026-04-29
- Reviewer: 
- Strategy/system version: 

## Evidence window
- Start date/time: 
- End date/time: 
- Trading days in window: 0
- Total paper trades: 0
- Data sources:
  - Audit export path: C:\Users\Nickos\jarvis\docs\reviews\artifacts\paper-audit-2026-04-29.jsonl
  - Trade replay report path: C:\Users\Nickos\jarvis\docs\reviews\artifacts\paper-trade-replay-2026-04-29.json
  - Trade performance report path: C:\Users\Nickos\jarvis\docs\reviews\artifacts\paper-trade-performance-2026-04-29.json
  - Audit export path:
  - Trade replay report path:

## Metrics
| Metric | Value | Threshold | Pass/Fail |
|---|---:|---:|---|
| Win rate | 0.0000 | > 0.5000 | FAIL |
| Profit factor | n/a | > 1.00 | FAIL |
| Max drawdown | 0.00 | <= 5000.00 | PASS |
| Avg R multiple | 0.00 | > 0.00 (proxy) | FAIL |
| Slippage/latency anomalies | 0 | <= 0 | PASS |
| Policy violations | 0 | 0 | PASS |

## Guardrail checks
- [ ] Review window >= 20 trading days OR >= 100 paper trades (whichever is later).
- [x] No unresolved policy bypass attempts.
- [x] No unexplained trade dispatch failures.
- [x] Drawdown stayed within configured daily and overall guardrails.
- [ ] `jarvis stop` rollback path tested.

## Notes
-

## Decision
- Decision: defer
- Conditions (if any):
- review_window_below_minimum, win_rate_below_minimum, profit_factor_below_minimum, avg_r_multiple_below_minimum

## Sign-off
- Reviewer signature:
- Operator signature:
- Sign-off timestamp:
