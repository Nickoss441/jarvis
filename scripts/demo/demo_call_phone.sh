#!/usr/bin/env bash
set -euo pipefail

export JARVIS_PHASE_APPROVALS=true
export JARVIS_PHASE_TELEPHONY=true
export JARVIS_CALL_PHONE_MODE=dry_run

python3 - <<'PY'
from jarvis.tools.call_phone import make_call_phone_tool
from jarvis.approval import ApprovalStore

store = ApprovalStore(".artifacts/demo-approvals.db")
tool = make_call_phone_tool(request_approval=store.request, get_approval=store.get)

result = tool.handler(phone_number="+14155552671", message="Demo reminder call")
print(result)
PY
