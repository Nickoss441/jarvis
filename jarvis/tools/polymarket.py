"""Polymarket public market query tool."""
from __future__ import annotations

import json
import urllib.parse
import urllib.request
from typing import Any

from . import Tool

_BASE = "https://gamma-api.polymarket.com"


def _get_json(path: str, params: dict[str, Any] | None = None) -> Any:
    query = ""
    if params:
        query = "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(_BASE + path + query, timeout=45) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _handler(action: str, query: str = "", limit: int = 10) -> dict[str, Any]:
    act = (action or "").strip().lower()
    lim = max(1, min(int(limit), 100))

    try:
        if act == "trending_markets":
            data = _get_json("/markets", {"limit": lim, "closed": "false"})
            return {"markets": data}

        if act == "search_markets":
            if not query.strip():
                return {"error": "query is required for search_markets"}
            data = _get_json("/markets", {"limit": lim, "closed": "false", "search": query.strip()})
            return {"markets": data}

        if act == "events":
            data = _get_json("/events", {"limit": lim, "closed": "false"})
            return {"events": data}

        return {"error": "unsupported action. use one of: trending_markets, search_markets, events"}
    except Exception as exc:  # noqa: BLE001
        return {"error": f"polymarket request failed: {exc}"}


polymarket = Tool(
    name="polymarket",
    description="Query Polymarket events and market odds.",
    input_schema={
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "description": "trending_markets|search_markets|events",
            },
            "query": {"type": "string"},
            "limit": {"type": "integer", "default": 10},
        },
        "required": ["action"],
    },
    handler=_handler,
    tier="open",
)
