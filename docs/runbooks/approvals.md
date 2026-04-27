# Approvals Runbook

## Purpose
Operate and troubleshoot the approval queue safely.

## Daily checks
- List pending approvals:
  - `python3 -m jarvis approvals-list`
- Dispatch approved items:
  - `python3 -m jarvis approvals-dispatch`
- Check audit chain health:
  - `python3 -m jarvis audit-verify`

## Common workflows

### Approve an item
1. List pending items.
2. Copy the `id`.
3. Approve with optional reason:
   - `python3 -m jarvis approvals-approve <id> "approved by operator"`
4. Dispatch:
   - `python3 -m jarvis approvals-dispatch`

### Reject an item
1. List pending items.
2. Reject with reason:
   - `python3 -m jarvis approvals-reject <id> "policy mismatch"`

### Investigate one action by correlation
- `python3 -m jarvis audit-correlation <correlation_id> --limit 100`

## TTL behavior
- Pending items auto-expire after `JARVIS_APPROVALS_TTL_SECONDS`.
- Expired items are marked rejected and produce `approval_expired` audit events.

## Safety notes
- Never dispatch blindly in bulk during incidents.
- Always include approval/reject reasons for high-risk actions.
- Keep `approvals_dispatch_max_per_run` conservative in production-like runs.
