# ADR 0001: Deterministic Policy Preflight

## Status
Accepted

## Context
LLM reasoning is non-deterministic and can be prompt-injected. Safety-critical boundaries must be deterministic and auditable.

## Decision
All tool calls pass through `Policy.check_tool(...)` before execution. Policy rules are data-driven from `policies.yaml` and enforced in runtime dispatch boundaries.

## Consequences
- Predictable denials with clear reasons.
- Centralized safety logic that is testable without model calls.
- Additional policy maintenance overhead when adding new tools.
