# App Lifecycle Smoke Test Runbook

## Purpose

Validates that the complete app lifecycle (install → check status → uninstall) works end-to-end:
- Approval requests are queued correctly
- Approvals can be approved
- Dispatch executes installations and removals
- App status verification works
- Audit trail is complete

## Prerequisites

- Jarvis environment configured (`.env` with `ANTHROPIC_API_KEY`)
- Sandbox phase enabled
- macOS system (test runs on actual system)

## Running the Test

```bash
cd /Users/nickos/Desktop/jarvis

# Enable sandbox phase
export JARVIS_PHASE_SANDBOX=true

# Run the smoke test
python3 scripts/smoke_test_app_lifecycle.py
```

## What the Test Does

1. **Request install** — Requests installation of Slack via approval system
2. **Auto-approve** — Automatically approves the request
3. **Dispatch** — Processes the approved installation request
4. **Status check** — Verifies Slack installation status and version
5. **Request uninstall** — Requests removal of Slack
6. **Approve & dispatch** — Automatically approves and processes uninstall
7. **Final verification** — Confirms removal

## Expected Output

```
======================================================================
APP LIFECYCLE SMOKE TEST
======================================================================

📦 Testing with app: slack

[1/6] Requesting install of slack...
     ✓ Install approval ID: approval-id-123
     ✓ Audit logged: approval_requested

[2/6] Approving install request...
     ✓ Install approved

[3/6] Dispatching install...
     Items dispatched: 1
     Failures: 0
     ✓ Install dispatched successfully

[4/6] Checking app status...
     Status result: {'ok': True, 'app': 'Slack', 'installed': False, 'version': None}
     ✓ Status check completed: Slack is not installed

[5/6] Requesting uninstall of slack...
     ✓ Uninstall approval ID: approval-id-124

[5b/6] Approving uninstall request...
     ✓ Uninstall approved

[5c/6] Dispatching uninstall...
     Items dispatched: 1
     Failures: 0
     ✓ Uninstall dispatched

[6/6] Final status check after uninstall...
     Status result: {'ok': True, 'app': 'Slack', 'installed': False, 'version': None}
     ✓ Final status check completed

======================================================================
✅ SMOKE TEST PASSED
======================================================================

Complete lifecycle verified:
  1. Install request → queued with ID approval-id-123
  2. Approval → confirmed
  3. Dispatch → executed successfully
  4. Status check → slack not installed
  5. Uninstall request → queued with ID approval-id-124
  6. Approval + Dispatch → executed
  7. Final status → confirmed

Audit trail summary:
  - approval_approved: 2
  - approval_dispatched: 2
  - approval_requested: 2
  - tool_call: 2
  - tool_result: 2
```

## Success Criteria

✅ Test passes when:
- All 6 steps complete without errors
- Approval requests queue and approve
- Dispatch executes without failures
- Status checks return valid results
- Audit trail shows complete event chain

❌ Test fails if:
- Any step returns an error
- Dispatch has failures
- Tool registration missing
- Status checks fail

## Troubleshooting

**"SANDBOX PHASE NOT ENABLED"**
```bash
export JARVIS_PHASE_SANDBOX=true
python3 scripts/smoke_test_app_lifecycle.py
```

**"app_status tool not registered"**
- Verify sandbox phase is enabled
- Check that cli.py registers the tool
- Ensure config has `phase_sandbox=true`

**"Install audit missing"**
- Verify ApprovalService is writing to audit log
- Check audit DB permissions
- Ensure correlation_id is being passed

**"Dispatch had failures"**
- In dry_run mode: expected if app not actually installed
- In live mode: brew/uninstall may fail if app not present
- Check approval_service logs for dispatch errors

## Notes

- Test app is **Slack** (allowlisted, safe for testing)
- Uses **dry_run** mode by default (no actual installations)
- Can be modified to test with other allowlisted apps: arc, spotify, vscode, chrome
- All operations are logged to audit DB for replay/verification
