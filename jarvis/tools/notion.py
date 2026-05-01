"""Notion API tool for page and database operations."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from . import Tool

_NOTION_API = "https://api.notion.com/v1"
_NOTION_VERSION = "2022-06-28"


def _request(method: str, path: str, token: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        _NOTION_API + path,
        method=method,
        data=data,
        headers={
            "Authorization": f"Bearer {token}",
            "Notion-Version": _NOTION_VERSION,
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=45) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _handler(
    action: str,
    query: str = "",
    page_id: str = "",
    database_id: str = "",
    properties: dict[str, Any] | None = None,
    children: list[dict[str, Any]] | None = None,
    filter: dict[str, Any] | None = None,  # noqa: A002
    page_size: int = 10,
) -> dict[str, Any]:
    token = os.environ.get("NOTION_API_KEY", "").strip()
    if not token:
        return {"error": "NOTION_API_KEY is not set."}

    act = (action or "").strip().lower()

    try:
        if act == "search":
            payload = {
                "query": query or "",
                "page_size": max(1, min(int(page_size), 100)),
            }
            return _request("POST", "/search", token, payload)

        if act == "get_page":
            if not page_id:
                return {"error": "page_id is required for get_page"}
            return _request("GET", f"/pages/{page_id}", token)

        if act == "create_page":
            if not properties:
                return {"error": "properties is required for create_page"}
            payload: dict[str, Any] = {"properties": properties}
            if database_id:
                payload["parent"] = {"database_id": database_id}
            elif page_id:
                payload["parent"] = {"page_id": page_id}
            else:
                return {"error": "database_id or page_id parent is required for create_page"}
            if children:
                payload["children"] = children
            return _request("POST", "/pages", token, payload)

        if act == "append_block":
            if not page_id:
                return {"error": "page_id is required for append_block"}
            if not children:
                return {"error": "children is required for append_block"}
            payload = {"children": children}
            return _request("PATCH", f"/blocks/{page_id}/children", token, payload)

        if act == "query_database":
            if not database_id:
                return {"error": "database_id is required for query_database"}
            payload: dict[str, Any] = {"page_size": max(1, min(int(page_size), 100))}
            if filter:
                payload["filter"] = filter
            return _request("POST", f"/databases/{database_id}/query", token, payload)

        return {
            "error": "unsupported action. use one of: search, get_page, create_page, append_block, query_database"
        }
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        return {"error": f"notion http error {exc.code}: {detail}"}
    except urllib.error.URLError as exc:
        return {"error": f"notion request failed: {exc.reason}"}
    except Exception as exc:  # noqa: BLE001
        return {"error": f"notion failed: {exc}"}


notion = Tool(
    name="notion",
    description="Manage Notion pages/databases via Notion API.",
    input_schema={
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "description": "search|get_page|create_page|append_block|query_database",
            },
            "query": {"type": "string"},
            "page_id": {"type": "string"},
            "database_id": {"type": "string"},
            "properties": {"type": "object"},
            "children": {"type": "array"},
            "filter": {"type": "object"},
            "page_size": {"type": "integer", "default": 10},
        },
        "required": ["action"],
    },
    handler=_handler,
    tier="open",
)
