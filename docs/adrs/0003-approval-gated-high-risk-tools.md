# ADR 0003: Approval-Gated High-Risk Tools

## Status
Accepted

## Context
Tools that spend money, contact third parties, trade, or execute shell commands can cause irreversible impact.

## Decision
Classify tools into open and gated tiers. Gated tools require explicit approval lifecycle (`requested -> approved/rejected -> dispatched`) and are always audited.

## Consequences
- Stronger human control and accountability for risky actions.
- Slightly slower workflows for high-risk operations.
- Clear separation of low-risk autonomy vs high-risk execution.
