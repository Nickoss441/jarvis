# Kill-Switch Runbook

## Purpose
Stop all automation and gated execution quickly.

## Trigger stop
- `python3 -m jarvis stop`

This creates `D:/jarvis-data/stopped` and signals the runtime to pause monitors and gated operations.

## Verify stopped state
- `ls D:/jarvis-data/stopped`
- `python3 -m jarvis approvals-dispatch`
  - Expect no active dispatch behavior while operational controls are paused.

## Resume
- `python3 -m jarvis resume`

## During incident
1. Trigger stop immediately.
2. Snapshot state:
   - `python3 -m jarvis audit-stats`
   - `python3 -m jarvis approvals-list`
3. Export audit for investigation:
   - `python3 -m jarvis audit-export > incident-audit.jsonl`
4. Perform root-cause analysis before resume.

## Post-incident
- Document timeline and affected correlations.
- Rotate any potentially exposed secrets.
- Add policy/test guardrails for recurrence.
