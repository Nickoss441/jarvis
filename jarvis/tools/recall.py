"""Recall over the audit log.

Phase 1: simple substring search. Phase 2 will add proper vector search
(LanceDB or sqlite-vss).
"""
from typing import Any

from . import Tool


def make_recall_tool(audit_log) -> Tool:
    def handler(query: str, limit: int = 20) -> dict[str, Any]:
        events = audit_log.recent(limit=500)
        q = query.lower()
        hits = [
            e for e in events
            if q in str(e.get("payload", "")).lower()
            or q in e.get("kind", "").lower()
        ][:limit]
        return {"matches": hits, "count": len(hits)}

    return Tool(
        name="recall",
        description=(
            "Search the agent's audit log for past events. Use when the user "
            "asks 'what did you do earlier' or 'remember when we...'."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "limit": {"type": "integer", "default": 20},
            },
            "required": ["query"],
        },
        handler=handler,
        tier="open",
    )
