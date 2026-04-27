# ADR 0002: Append-Only Hash-Chained Audit

## Status
Accepted

## Context
The project needs replayability and tamper evidence without heavy infrastructure.

## Decision
Use SQLite append-only events with a SHA-256 hash chain (`prev_hash` -> `hash`) and verification via `audit-verify`.

## Consequences
- Lightweight, local-first audit storage.
- Tamper detection is simple and fast.
- Direct row mutation breaks chain integrity by design.
