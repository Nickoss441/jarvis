# Jarvis Desktop Quickstart

**Version:** v0.2-trading-unlock  
**Status:** ✅ Production Ready

## Quick Start (30 seconds)

```bash
cd /Users/nickos/Desktop/jarvis
bash jarvis-start.sh
```

Then open browser to: **http://127.0.0.1:8080**

## What's Included

### ✅ Core Features (Phase 1-3)
- **Approval System**: Gated tool execution with human sign-off
- **Audit Trail**: Append-only hash-chain logging of all actions  
- **Event Bus**: Real-time event processing and automation
- **Trading (Paper Mode)**: Risk-controlled paper trading with safeguards

### ✅ Phase 5: Trading Unlock Validation (NEW)
- **Backtesting Integration**: 150-trade scenario test passing all metrics
- **Position Safeguards**: 2% equity position cap enforced
- **Daily Drawdown Limit**: 5% equity protection kill-switch
- **Performance Review Artifact**: Auto-generated unlock readiness report

### 📋 Ready-to-Use CLI Commands

```bash
# Audit & compliance
python3 -m jarvis audit-stats          # View chain stats
python3 -m jarvis audit-verify         # Verify chain integrity
python3 -m jarvis audit-export         # Export JSONL log

# Trading
python3 -m jarvis trade-performance-report --mode paper
python3 -m jarvis trade-review-artifact --reviewer "You"

# Approvals
python3 -m jarvis approvals-list       # View pending approvals
python3 -m jarvis approvals-seed 5     # Create test approvals

# Events
python3 -m jarvis events-list          # View events
python3 -m jarvis events-stats         # Event summary
python3 -m jarvis events-process       # Process events

# Locations & tools
python3 -m jarvis location-update 37.7749 -122.4194  # Update location
python3 -m jarvis location-last        # Get last location
```

## Architecture

```
Desktop/jarvis/
├── jarvis/                  # Main package
│   ├── approval*.py        # Approval gating system
│   ├── audit.py            # Audit trail (hash chain)
│   ├── event_bus.py        # Event processing
│   ├── tools/              # Open & gated tool implementations
│   │   └── trade.py        # Trading tool (paper + live)
│   ├── config.py           # Configuration management
│   └── trade_review.py     # Trade review artifact generation
├── tests/                   # 775 comprehensive tests
│   └── test_trade.py       # 6 new backtesting + safeguard tests
├── docs/
│   ├── runbooks/           # Operational procedures
│   │   └── live-trading-unlock.md  # PHASE 5 unlock guide
│   └── reviews/artifacts/  # Trade review artifacts
├── .env.local              # Development config (git-ignored)
└── requirements.txt        # Python dependencies (installed)
```

## Running on Desktop

### 1. Start the Server

```bash
bash jarvis-start.sh
# or manually:
cd /Users/nickos/Desktop/jarvis
set -a && source .env.local && set +a
python3 -m jarvis approvals-api
```

Output:
```
Approval API listening on http://127.0.0.1:8080
```

### 2. Open Web UI

Browse to: **http://127.0.0.1:8080**

You'll see:
- Pending approvals queue
- Approve/reject buttons
- Dispatch controls
- Audit trail viewer

### 3. Test with Sample Approvals

```bash
python3 -m jarvis approvals-seed 3    # Create 3 test approvals
```

Then in the web UI, click "Approve" or "Reject" on any pending approval.

### 4. Check Audit Log

```bash
python3 -m jarvis audit-stats
# Output: chain_length: X, kinds: {...}

python3 -m jarvis audit-export | head  # View first entries
```

## Testing Trading Features

### Generate Paper Trading Review

```bash
python3 -m jarvis trade-review-artifact \
  --reviewer "Your Name" \
  --strategy-version "v1.0.0"
```

Produces:
- `docs/reviews/paper-performance-review-YYYY-MM-DD.md`  — Human-readable review
- `docs/reviews/artifacts/paper-audit-YYYY-MM-DD.jsonl` — Audit export
- `docs/reviews/artifacts/paper-trade-replay-YYYY-MM-DD.json` — Trade replay
- `docs/reviews/artifacts/paper-trade-performance-YYYY-MM-DD.json` — Metrics

### Run Trading Tests

```bash
python3 -m pytest tests/test_trade.py -v

# Specifically test backtesting & safeguards:
python3 -m pytest tests/test_trade.py::test_backtesting_integration_generates_unlockable_performance_review -v
python3 -m pytest tests/test_trade.py::test_position_size_safeguard_prevents_oversized_trades -v
python3 -m pytest tests/test_trade.py::test_daily_drawdown_safeguard_pauses_trades -v
```

## Configuration

All settings in **`.env.local`** (git-ignored):

```env
# Your API keys (replace PLACEHOLDER)
ANTHROPIC_API_KEY=sk-ant-v1-...

# Phase toggles
JARVIS_PHASE_APPROVALS=true        # Approval gating
JARVIS_PHASE_TRADING=true          # Trading features

# Trading params
JARVIS_TRADING_ACCOUNT_EQUITY=100000
JARVIS_TRADING_DAILY_DRAWDOWN_KILL_PCT=5.0
JARVIS_TRADING_REVIEW_MIN_WIN_RATE=0.70
JARVIS_TRADING_REVIEW_MIN_PROFIT_FACTOR=1.50

# Servers
JARVIS_APPROVALS_API_HOST=127.0.0.1
JARVIS_APPROVALS_API_PORT=8080

# Paths (default: ~/.jarvis-dev/)
JARVIS_AUDIT_DB=~/.jarvis-dev/audit.db
JARVIS_TRADES_LOG=~/.jarvis-dev/trades-log.jsonl
```

## Safety & Controls

### Approval Workflow
Every gated tool (trade, message, call, payment) requires approval before dispatch:

1. **Tool Request** → Approval created (TTL: 15 min default)
2. **Human Review** → Web UI shows pending request
3. **Approve/Reject** → Manual decision (5-second cooldown default)
4. **Dispatch** → Tool executes with audit trail

### Trading Safeguards
- **Position Cap**: 2% of account equity per trade (enforced)
- **Daily Loss Limit**: 5% kill-switch (pauses new trades)
- **Per-Trade Confirm**: Live mode requires explicit `live_confirm` flag
- **Paper-First**: Unlock only after documented paper performance

### Kill Switch
```bash
python3 -m jarvis stop      # Pause monitors + reject new approvals
python3 -m jarvis resume    # Resume operation
```

## Files Changed (v0.2)

```
tests/test_trade.py              +344 lines (6 new tests)
docs/runbooks/live-trading-unlock.md  +234 lines (NEW)
docs/reviews/artifacts/*         +4641 lines (trade artifacts)
```

**Total tests:** 775 passing ✅

## Troubleshooting

**Q: "ANTHROPIC_API_KEY not found"**  
A: Replace `PLACEHOLDER` in `.env.local` with your actual key.

**Q: Port 8080 already in use**  
A: Change in `.env.local`:
```env
JARVIS_APPROVALS_API_PORT=8081
```

**Q: Tests fail**  
A: Run the full suite:
```bash
make verify  # Tests + lint + audit verify
```

**Q: Can't access http://127.0.0.1:8080**  
A: Verify server started:
```bash
ps aux | grep "approvals-api"
curl -v http://127.0.0.1:8080
```

## Next Steps

1. **Request approval** via tool invocation or web UI
2. **Review and approve** in the browser
3. **Check audit trail** for compliance
4. **Run tests** to validate changes
5. **Generate trade review** for unlock readiness (Phase 6)

## Documentation

- [Architecture](ARCHITECTURE.md) — System design overview
- [Approvals Runbook](docs/runbooks/approvals.md) — Approval workflow
- [Live Trading Unlock](docs/runbooks/live-trading-unlock.md) — **NEW** Phase 5 procedure
- [Incident Response](docs/runbooks/incident-response.md) — Emergency procedures

## Repository

- **GitHub:** https://github.com/Nickoss441/jarvis
- **Latest Release:** v0.2-trading-unlock
- **Main Branch:** Production-ready, all tests passing

---

**Ready to go!** 🚀 Start the server and approve your first action in the web UI.
