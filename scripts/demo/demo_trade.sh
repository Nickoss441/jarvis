#!/usr/bin/env bash
set -euo pipefail

export JARVIS_PHASE_APPROVALS=true
export JARVIS_PHASE_TRADING=true
export JARVIS_TRADES_MODE=dry_run

python3 - <<'PY'
from jarvis.tools.trade import make_trade_tool
from jarvis.approval import ApprovalStore

store = ApprovalStore(".artifacts/demo-approvals.db")
tool = make_trade_tool(request_approval=store.request, get_approval=store.get)

result = tool.handler(instrument="AAPL", side="buy", size=1, rationale="Demo trade")
print(result)
PY
