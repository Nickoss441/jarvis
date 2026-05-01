"""Slack Web API tool for messaging and channel reads."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from . import Tool

_SLACK_API = "https://slack.com/api"


def _call(endpoint: str, token: str, payload: dict[str, Any]) -> dict[str, Any]:
    data = urllib.parse.urlencode(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{_SLACK_API}/{endpoint}",
        method="POST",
        data=data,
        headers={"Authorization": f"Bearer {token}"},
    )
    with urllib.request.urlopen(req, timeout=45) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _handler(
    action: str,
    channel: str = "",
    text: str = "",
    timestamp: str = "",
    emoji: str = "",
    limit: int = 20,
) -> dict[str, Any]:
    token = os.environ.get("SLACK_BOT_TOKEN", "").strip()
    if not token:
        return {"error": "SLACK_BOT_TOKEN is not set."}

    act = (action or "").strip().lower()

    try:
        if act == "post_message":
            if not channel or not text:
                return {"error": "channel and text are required for post_message"}
            return _call("chat.postMessage", token, {"channel": channel, "text": text})

        if act == "history":
            if not channel:
                return {"error": "channel is required for history"}
            return _call(
                "conversations.history",
                token,
                {"channel": channel, "limit": str(max(1, min(int(limit), 200)))},
            )

        if act == "add_reaction":
            if not channel or not timestamp or not emoji:
                return {"error": "channel, timestamp, and emoji are required for add_reaction"}
            return _call(
                "reactions.add",
                token,
                {"channel": channel, "timestamp": timestamp, "name": emoji},
            )

        return {"error": "unsupported action. use one of: post_message, history, add_reaction"}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        return {"error": f"slack http error {exc.code}: {detail}"}
    except urllib.error.URLError as exc:
        return {"error": f"slack request failed: {exc.reason}"}
    except Exception as exc:  # noqa: BLE001
        return {"error": f"slack failed: {exc}"}


slack = Tool(
    name="slack",
    description="Send/read Slack messages and add reactions via Slack Web API.",
    input_schema={
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "description": "post_message|history|add_reaction",
            },
            "channel": {"type": "string"},
            "text": {"type": "string"},
            "timestamp": {"type": "string"},
            "emoji": {"type": "string"},
            "limit": {"type": "integer", "default": 20},
        },
        "required": ["action"],
    },
    handler=_handler,
    tier="open",
)
