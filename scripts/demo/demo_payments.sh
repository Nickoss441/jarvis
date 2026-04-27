#!/usr/bin/env bash
set -euo pipefail

export JARVIS_PHASE_APPROVALS=true
export JARVIS_PHASE_PAYMENTS=true
export JARVIS_PAYMENTS_MODE=dry_run

python3 - <<'PY'
from jarvis.tools.payments import make_payments_tool
from jarvis.approval import ApprovalStore

store = ApprovalStore(".artifacts/demo-approvals.db")
tool = make_payments_tool(request_approval=store.request, get_approval=store.get)

result = tool.handler(amount=12.50, currency="USD", recipient="merchant-demo", reason="Demo purchase")
print(result)
PY
