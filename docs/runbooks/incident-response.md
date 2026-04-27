# Incident Response Runbook

## Severity levels
- SEV-1: unsafe financial/telephony behavior or potential secret compromise
- SEV-2: approval/dispatch failures causing blocked operations
- SEV-3: degraded monitor/tool behavior without safety impact

## Immediate triage
1. Activate kill switch for SEV-1/SEV-2:
   - `python3 -m jarvis stop`
2. Capture evidence:
   - `python3 -m jarvis audit-stats`
   - `python3 -m jarvis approvals-list`
   - `python3 -m jarvis events-stats`
3. Export logs:
   - `python3 -m jarvis audit-export > incident-audit.jsonl`

## Investigation checklist
- Confirm audit chain integrity (`audit-verify`).
- Identify first bad correlation id.
- Inspect related approvals and dispatch results.
- Check policy decisions around blocked/allowed transitions.
- Verify idempotency behavior for duplicates.

## Containment
- Keep automation stopped until fix is validated.
- Tighten policy temporarily (block risky tools/domains).
- Reduce dispatch throughput and risk tiers if needed.

## Recovery
1. Apply fix and add regression tests.
2. Run focused tests, then full-suite tail check.
3. Resume:
   - `python3 -m jarvis resume`
4. Monitor for recurrence for at least one full business cycle.

## Postmortem requirements
- Impact summary
- Timeline with UTC timestamps
- Root cause
- Corrective/preventive actions
- Owner and deadline for each action
