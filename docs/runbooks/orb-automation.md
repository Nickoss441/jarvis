# Orb Automation Runbook

## Purpose
Automate orb/city data auditing so issues are detected and reported without manual review.

## Command
Run from repo root:

```bash
python scripts/orb_task_automation.py
```

Or use Make:

```bash
make orb-audit
```

## Outputs
Each run updates:

- `jarvis/web/hud_react/data/canonical_orbs.json`
- `docs/reports/orb_audit_report.md`

## What It Automates
- Extracts orb data from:
  - `GLOBE_MARKERS`
  - `MARKETS`
  - `MAJOR_CITY_DOTS`
- Builds a canonical deduplicated city-orb dataset
- Validates coordinate ranges
- Flags coordinate divergence across duplicate city sources
- Produces a human-readable audit report

## Exit Codes
- `0`: Run completed with no hard errors
- `2`: Coordinate validation errors found

## Overnight / Unattended Mode
Use a scheduled task/cron equivalent to run:

```bash
make orb-audit
```

Then inspect `docs/reports/orb_audit_report.md` for findings.
