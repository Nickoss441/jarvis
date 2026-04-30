# Live Trading Unlock Runbook

## Purpose
Enable live-mode trading on Jarvis after documented paper-trading performance review and manual sign-off.

## Prerequisites
- Paper trading must be running and accumulating trades.
- Minimum evidence window: 20 trading days OR 100 paper trades (whichever is later).
- All auto-checks pass in the trade review artifact.
- Operator has reviewed and signed off on the performance review.

## Step 1: Generate Paper Performance Review Artifact

Run the automated review generator:

```bash
python3 -m jarvis trade-review-artifact \
  --reviewer "Your Name" \
  --strategy-version "v1.2.3" \
  --output ./docs/reviews/paper-performance-review-YYYY-MM-DD.md
```

This produces:
- **Markdown review** with metrics table and auto-checks
- **Audit export** (JSONL) of all trade-related events
- **Trade replay report** (JSON) showing trade sequence and outcomes
- **Trade performance report** (JSON) with detailed statistics

## Step 2: Verify Auto-Checks Pass

The review artifact includes auto-decision logic:

| Auto-Check | Requirement | Source |
|---|---|---|
| Review window | ≥ 20 trading days OR 100 trades | Trade count + date range |
| Win rate | ≥ Min threshold (default 0.70) | Profit/loss count |
| Profit factor | > Min threshold (default 1.50) | Gross profit / gross loss |
| Avg R multiple | > Min threshold (default 0.50) | Return-on-risk proxy |
| Anomalies | ≤ Max budget (default 5) | Latency + slippage count |
| Policy violations | = 0 | Audit log inspection |
| Dispatch failures | = 0 | Trade approval + dispatch events |
| Drawdown guardrail | ≤ Daily+overall limit | Max drawdown vs equity |

**Expected outcome:**  
If all auto-checks pass, the artifact decision is: **"ready for manual sign-off"**

**If any fail:**  
The artifact decision is: **"defer"** with detailed reasons. Do NOT proceed to live unlock until all pass.

## Step 3: Review Markdown Artifact

Open the generated markdown file and:

1. **Check metadata:**
   - Review date and period correct?
   - Reviewer name and strategy version populated?

2. **Inspect metrics:**
   - All metric rows show `PASS`?
   - Win rate, profit factor, and R multiple align with your expectations?
   - Max drawdown within acceptable risk bounds?

3. **Verify evidence links:**
   - Do audit, replay, and performance JSON files exist?
   - Can you spot-check 5-10 trades in the replay report?

4. **Review guardrail checks:**
   - Window size sufficient?
   - No policy bypass attempts noted?
   - No unexplained dispatch failures?
   - Drawdown stayed under kill-switch threshold?

## Step 4: Test Rollback Path

Before enabling live mode, ensure you can quickly stop Jarvis:

```bash
python3 -m jarvis stop
# Verify kill-switch active
ls -la D:/jarvis-data/stopped

# Later, resume:
python3 -m jarvis resume
```

This confirms the `jarvis stop` emergency control works.

## Step 5: Enable Live Mode

Set the feature flag to allow live-mode trades:

```bash
export JARVIS_TRADING_PHASE_6_LIVE_UNLOCK=true
```

Or persist in your `.env`:

```env
JARVIS_TRADING_PHASE_6_LIVE_UNLOCK=true
```

Start (or restart) Jarvis:

```bash
python3 -m jarvis run
```

## Step 6: Verify Live Readiness

Check that live mode is armed:

```bash
curl -s http://localhost:8000/trading/config | jq '.live_mode_enabled'
# Should return: true
```

Verify that per-trade approvals still enforce:

```bash
curl -s http://localhost:8000/trading/status | jq '.requires_per_trade_confirm'
# Should return: true (cooling period still applies)
```

## Step 7: Start with Small Position Sizes

On first live trades:
- Keep position sizes at **25% of normal** for first 5 trades.
- Monitor P&L closely for slippage or execution differences vs. paper.
- Gradually increase to normal sizing over 10-20 trades if all looks good.

## Step 8: Monitor Daily Drawdown

Live mode enforces the configured daily loss limit. Example config:

```env
JARVIS_TRADING_ACCOUNT_EQUITY=50000
JARVIS_TRADING_DAILY_DRAWDOWN_KILL_PCT=5.0  # = $2,500 max daily loss
```

If daily loss exceeds this threshold:
- All new trade proposals are auto-denied with `"daily drawdown pause active"` reason.
- Manual `jarvis stop` is still available for emergency halt.
- Drawdown counter resets at next trading day (UTC midnight).

## Step 9: Document Go/No-Go Decision

In the markdown review file, complete the **Sign-off** section:

```markdown
## Sign-off
- Reviewer signature: (Your Name)
- Operator signature: (Ops team approval)
- Sign-off timestamp: YYYY-MM-DD HH:MM UTC
```

Commit the review artifact to version control:

```bash
git add docs/reviews/paper-performance-review-YYYY-MM-DD.md
git add docs/reviews/artifacts/
git commit -m "docs: live trading unlock approved - $(date +%Y-%m-%d)"
git push
```

## Safety Considerations

1. **Per-trade confirmation still required:**
   - Even with `JARVIS_TRADING_PHASE_6_LIVE_UNLOCK=true`, each live trade still requires approval.
   - Default approval cooldown: 5 seconds (configurable).
   - This gives you time to review before dispatch.

2. **Daily drawdown kill-switch:**
   - If you hit the daily loss threshold, all new proposals are auto-rejected.
   - Reset at UTC midnight.
   - Can be manually overridden with `jarvis resume` after drawdown resets.

3. **Policy checks still apply:**
   - Domain blocks, critical smart-home restrictions, rate limits all still active.
   - No trades can bypass configured policy rules.

4. **Emergency rollback:**
   - `jarvis stop` immediately pauses all monitors and rejects new approvals.
   - Does NOT cancel open positions (broker-side manual required).
   - Recoverable with `jarvis resume`.

## Troubleshooting

### "dispatch_failures_detected" in artifact?
- Check approval service logs for why trade proposals failed to dispatch.
- Verify account credentials and order endpoint connectivity.
- Review broker-side errors in the audit trail.

### Win rate below threshold?
- Paper trading strategy may need refinement.
- Check for test-fixture biases (tick size, slippage, commissions).
- Extend review window to 50+ trades for statistical significance.

### Drawdown exceeded guardrail?
- Increase position sizing cap or reduce max-daily-drawdown % if limits are too tight.
- Or: reduce strategy aggressiveness (fewer positions, tighter stops).
- Re-run paper trades with adjusted params before re-attempting unlock.

### "policy_bypass_detected" in artifact?
- Audit log shows attempted override of policy rules.
- Investigate why approvals granted against policy.
- Review and tighten approval workflow if needed.

## Reverting Live Mode

If live trading proves unstable, disable immediately:

```bash
export JARVIS_TRADING_PHASE_6_LIVE_UNLOCK=false
# OR
python3 -m jarvis stop
```

Document the revert in a new runbook entry:

```bash
cat >> docs/runbooks/live-trading-unlock.md << 'EOF'

## Live Mode Disabled [DATE]
- Reason: [Brief summary]
- Timestamp: [UTC]
- Next review date: [Date]
EOF
```

## Related Runbooks
- [Paper Trading Review](./paper-trading-review.md) — Generate the performance artifact
- [Incident Response](./incident-response.md) — Respond to trading anomalies
- [Kill Switch](./kill-switch.md) — Emergency stop procedures
- [Key Rotation](./key-rotation.md) — Secure credential updates
