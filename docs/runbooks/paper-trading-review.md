# Paper Trading Performance Review Runbook

## Purpose
Document objective paper-trading performance before enabling live trading.

## Required evidence window
- Minimum review window: 20 trading days (or 100 paper trades, whichever is later).
- Data source: immutable audit trail + trade log.
- These defaults are configurable via env vars:
   - `JARVIS_TRADING_REVIEW_MIN_TRADING_DAYS`
   - `JARVIS_TRADING_REVIEW_MIN_TRADES`
   - `JARVIS_TRADING_REVIEW_MIN_WIN_RATE`
   - `JARVIS_TRADING_REVIEW_MIN_PROFIT_FACTOR`
   - `JARVIS_TRADING_REVIEW_MIN_AVG_R_MULTIPLE`
   - `JARVIS_TRADING_REVIEW_MAX_ANOMALIES`

## Required metrics
- Win rate
- Profit factor
- Max drawdown
- Average R multiple / risk-adjusted return proxy
- Slippage/latency anomalies count
- Policy violation count (must be zero for unlock)

## Collection steps
1. Export audit:
   - `python3 -m jarvis audit-export > paper-audit.jsonl`
2. Generate trade replay report:
   - `python3 -m jarvis trade-replay-report --limit 500 > paper-trade-replay.json`
3. Generate the review package directly:
   - `python3 -m jarvis trade-review-artifact --reviewer <name> --strategy-version <ver>`
4. Optional raw performance summary:
   - `python3 -m jarvis trade-performance-report --mode paper > paper-trade-performance.json`
5. Review the generated markdown artifact and complete human sign-off fields.

## Unlock checklist
- [ ] Review window meets minimum size.
- [ ] No unresolved policy-denied bypass attempts.
- [ ] No unexplained dispatch failures for trade actions.
- [ ] Drawdown remained within configured guardrails.
- [ ] Operator sign-off recorded.
- [ ] Rollback plan prepared (`jarvis stop` path tested).

## Decision record
- Review period:
- Reviewer:
- Decision: `approve live unlock` / `defer`
- Notes:

## Safety note
Even after approval, live mode still requires per-trade confirmation and cooldown safeguards.
