# Paper Performance Review Record Template

Use this file to produce the concrete artifact required before live trading unlock.

## Metadata
- Review ID:
- Review date:
- Reviewer:
- Strategy/system version:

## Evidence window
- Start date/time:
- End date/time:
- Trading days in window:
- Total paper trades:
- Data sources:
  - Audit export path:
  - Trade replay report path:

## Metrics
| Metric | Value | Threshold | Pass/Fail |
|---|---:|---:|---|
| Win rate |  |  |  |
| Profit factor |  |  |  |
| Max drawdown |  |  |  |
| Avg R multiple |  |  |  |
| Slippage/latency anomalies |  |  |  |
| Policy violations |  | 0 |  |

## Guardrail checks
- [ ] Review window >= 20 trading days OR >= 100 paper trades (whichever is later).
- [ ] No unresolved policy bypass attempts.
- [ ] No unexplained trade dispatch failures.
- [ ] Drawdown stayed within configured daily and overall guardrails.
- [ ] `jarvis stop` rollback path tested.

## Notes
-

## Decision
- Decision: approve live unlock / defer
- Conditions (if any):
-

## Sign-off
- Reviewer signature:
- Operator signature:
- Sign-off timestamp:
