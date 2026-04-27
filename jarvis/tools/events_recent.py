"""Expose recent perception events to the agent.

This gives the LLM a safe, read-only view into the EventBus so it can answer
questions like "what happened recently" and react to fresh monitor events.
"""

from __future__ import annotations

from typing import Any

from ..event_bus import EventBus
from . import Tool


def make_events_recent_tool(event_bus: EventBus) -> Tool:
    def handler(
        limit: int = 20,
        kind: str | None = None,
        unprocessed_only: bool = False,
    ) -> dict[str, Any]:
        safe_limit = max(1, min(int(limit), 200))

        if unprocessed_only:
            events = event_bus.list_unprocessed(limit=safe_limit, kind=kind)
        else:
            events = event_bus.recent(limit=safe_limit, kind=kind)

        return {
            "count": len(events),
            "limit": safe_limit,
            "kind": kind,
            "unprocessed_only": bool(unprocessed_only),
            "events": [
                {
                    "id": e.id,
                    "kind": e.kind,
                    "source": e.source,
                    "timestamp": e.timestamp,
                    "correlation_id": e.correlation_id,
                    "processed": e.processed,
                    "processed_at": e.processed_at,
                    "notes": e.notes,
                    "payload": e.payload,
                }
                for e in events
            ],
        }

    return Tool(
        name="events_recent",
        description=(
            "List recent perception events from the local EventBus. Use this "
            "to inspect monitor activity or check unprocessed events before "
            "taking action."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "default": 20},
                "kind": {"type": "string"},
                "unprocessed_only": {"type": "boolean", "default": False},
            },
        },
        handler=handler,
        tier="open",
    )
