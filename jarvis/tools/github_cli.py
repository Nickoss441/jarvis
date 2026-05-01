"""GitHub CLI tool wrapper for Jarvis.

Requires GitHub CLI (`gh`) to be installed and authenticated.
"""
from __future__ import annotations

import shlex
import shutil
import subprocess
from typing import Any

from . import Tool

_ALLOWED_ROOT = {
    "issue",
    "pr",
    "run",
    "repo",
    "search",
    "api",
    "workflow",
    "release",
    "gist",
    "auth",
    "status",
}


def _handler(command: str, timeout_seconds: int = 90) -> dict[str, Any]:
    cmd = (command or "").strip()
    if not cmd:
        return {"error": "command is required (example: 'issue list --limit 5')."}

    if shutil.which("gh") is None:
        return {
            "error": "GitHub CLI not found. Install it from https://cli.github.com/"
        }

    try:
        parts = shlex.split(cmd)
    except ValueError as exc:
        return {"error": f"invalid command syntax: {exc}"}

    if not parts:
        return {"error": "command parsed to empty argument list."}

    root = parts[0].lower()
    if root not in _ALLOWED_ROOT:
        return {
            "error": (
                "unsupported gh command root. allowed: "
                + ", ".join(sorted(_ALLOWED_ROOT))
            )
        }

    timeout = max(5, min(int(timeout_seconds), 300))
    argv = ["gh", *parts]

    try:
        proc = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {"error": f"gh command timed out after {timeout}s"}
    except Exception as exc:  # noqa: BLE001
        return {"error": f"gh command failed to start: {exc}"}

    return {
        "ok": proc.returncode == 0,
        "exit_code": proc.returncode,
        "stdout": proc.stdout.strip(),
        "stderr": proc.stderr.strip(),
        "command": cmd,
    }


github_cli = Tool(
    name="github_cli",
    description=(
        "Run GitHub CLI commands for issues, pull requests, runs, and API queries. "
        "Requires gh to be installed/authenticated."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "gh subcommand without the leading 'gh' (example: 'issue list --limit 5')",
            },
            "timeout_seconds": {
                "type": "integer",
                "description": "Execution timeout in seconds (default 90, max 300)",
                "default": 90,
            },
        },
        "required": ["command"],
    },
    handler=_handler,
    tier="open",
)
