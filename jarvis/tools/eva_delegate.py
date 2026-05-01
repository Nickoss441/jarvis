"""Delegate a task to EVA (OpenClaw model on Ollama).

Jarvis calls this tool when a task benefits from EVA's 100+ skill set:
computer control, file ops, web research, coding, automation, etc.
EVA runs locally — zero API cost, zero cloud dependency.

Usage by Jarvis:
    eva_delegate(task="Search the web for today's GPU prices and summarise")
    eva_delegate(task="Write a Python script that...", context="We were discussing X")
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from . import Tool

# Path to the soul file so EVA stays in character.
_EVA_SYSTEM = """\
You are E.V.A. (Electronic Virtual Assistant), a Tactical Strategist AI built by Jarvis.
Your role: execute tasks precisely and return clean, structured results.
Rules:
- Be direct and concise.  No filler.
- Use your skills (web, files, code, calendar, system) to complete the task fully.
- Return results in a format Jarvis can relay to the Operator.
- Address gaps as "Insufficient Data" and propose a recovery path.
"""

_OLLAMA_URL = "http://localhost:11434/api/chat"
_DEFAULT_MODEL = "openclaw"
_TIMEOUT = 90  # seconds


def _call_eva(task: str, context: str, model: str) -> dict[str, Any]:
    messages: list[dict[str, str]] = []
    if context:
        messages.append({"role": "user", "content": f"[Context from Jarvis]: {context}"})
        messages.append({"role": "assistant", "content": "Context received. Ready."})
    messages.append({"role": "user", "content": task})

    payload = json.dumps(
        {
            "model": model,
            "messages": messages,
            "system": _EVA_SYSTEM,
            "stream": False,
        }
    ).encode()

    req = urllib.request.Request(
        _OLLAMA_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
        data = json.loads(resp.read())

    return {
        "agent": "eva",
        "model": data.get("model", model),
        "response": data.get("message", {}).get("content", ""),
    }


def _handler(task: str, context: str = "", model: str = _DEFAULT_MODEL) -> dict[str, Any]:
    if not task or not task.strip():
        return {"error": "task is required — describe what EVA should do."}
    try:
        return _call_eva(task.strip(), context.strip(), model)
    except urllib.error.URLError as exc:
        return {
            "error": (
                f"EVA is offline: {exc.reason}. "
                "Start her with: ollama run openclaw"
            )
        }
    except TimeoutError:
        return {"error": f"EVA timed out after {_TIMEOUT}s. Try a simpler task or increase timeout."}
    except Exception as exc:  # noqa: BLE001
        return {"error": f"EVA error: {exc}"}


eva_delegate = Tool(
    name="eva_delegate",
    description=(
        "Delegate a task to EVA — your AI partner running OpenClaw on Ollama (local, free). "
        "Best for: web research, file operations, code generation, computer control, "
        "system automation, calendar/scheduling, and any task with 100+ OpenClaw skills. "
        "EVA returns a structured result that Jarvis relays to the Operator. "
        "Always prefer EVA for skill-heavy execution tasks."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "task": {
                "type": "string",
                "description": (
                    "The specific task for EVA to execute. Be precise — "
                    "e.g. 'Search the web for the current BTC price and return the top 3 sources.'"
                ),
            },
            "context": {
                "type": "string",
                "description": (
                    "Optional: relevant context from the current conversation "
                    "so EVA has background before executing."
                ),
            },
            "model": {
                "type": "string",
                "description": (
                    "Ollama model to use for EVA. Defaults to 'openclaw'. "
                    "Override only if you have a custom EVA-optimised model installed."
                ),
            },
        },
        "required": ["task"],
    },
    handler=_handler,
)
