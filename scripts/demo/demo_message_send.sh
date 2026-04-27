#!/usr/bin/env bash
set -euo pipefail

export JARVIS_PHASE_APPROVALS=true
export JARVIS_MESSAGE_SEND_MODE=dry_run

python3 - <<'PY'
from jarvis.tools.message_send import make_message_send_tool
from jarvis.approval import ApprovalStore

store = ApprovalStore(".artifacts/demo-approvals.db")
tool = make_message_send_tool(request_approval=store.request, get_approval=store.get)

result = tool.handler(channel="email", recipient="user@example.com", body="Demo dry-run message")
print(result)
PY
