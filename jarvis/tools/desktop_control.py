"""Desktop control tool for local macOS automation.

This tool is intentionally constrained and intended for local operator workflows.
It supports a small set of actions:
- open_app: launch or focus an app by name
- open_url: open a URL with the default handler
- keystroke: send a key combo using AppleScript System Events
- type_text: type plain text into the focused app

Register only when phase_sandbox is enabled.
"""
from __future__ import annotations

import platform
import re
import subprocess
from typing import Any

from . import Tool

_MAX_TEXT_CHARS = 500
_VALID_ACTIONS = {"open_app", "open_url", "keystroke", "type_text"}
_KEY_COMBO_PATTERN = re.compile(r"^[A-Za-z0-9+\-_ ]{1,60}$")


def _run_command(argv: list[str]) -> tuple[bool, str]:
    try:
        out = subprocess.run(  # noqa: S603
            argv,
            capture_output=True,
            text=True,
            timeout=15,
        )
    except subprocess.TimeoutExpired:
        return False, "command timed out"
    except FileNotFoundError:
        return False, "required executable not found"

    if out.returncode != 0:
        msg = (out.stderr or out.stdout or "command failed").strip()
        return False, msg[:800]
    return True, (out.stdout or "ok").strip()[:800]


def make_desktop_control_tool(mode: str = "live") -> Tool:
    """Build a constrained desktop automation tool."""

    def _handle(
        action: str,
        app: str = "",
        url: str = "",
        key_combo: str = "",
        text: str = "",
        **_: Any,
    ) -> dict[str, Any]:
        act = (action or "").strip().lower()
        if act not in _VALID_ACTIONS:
            return {"ok": False, "error": f"unsupported action '{action}'"}

        if mode == "dry_run":
            return {
                "ok": True,
                "mode": "dry_run",
                "action": act,
                "app": app,
                "url": url,
                "key_combo": key_combo,
                "text_preview": text[:120],
            }

        if platform.system() != "Darwin":
            return {"ok": False, "error": "desktop_control currently supports macOS only"}

        if act == "open_app":
            app_name = app.strip()
            if not app_name:
                return {"ok": False, "error": "app is required for open_app"}
            ok, detail = _run_command(["open", "-a", app_name])
            return {"ok": ok, "action": act, "detail": detail, "app": app_name}

        if act == "open_url":
            target = url.strip()
            if not target:
                return {"ok": False, "error": "url is required for open_url"}
            if not (target.startswith("http://") or target.startswith("https://") or target.startswith("file://")):
                return {"ok": False, "error": "url must start with http://, https://, or file://"}
            ok, detail = _run_command(["open", target])
            return {"ok": ok, "action": act, "detail": detail, "url": target}

        if act == "keystroke":
            combo = key_combo.strip()
            if not combo:
                return {"ok": False, "error": "key_combo is required for keystroke"}
            if not _KEY_COMBO_PATTERN.fullmatch(combo):
                return {"ok": False, "error": "key_combo contains unsupported characters"}
            script = (
                'tell application "System Events"\n'
                f'  keystroke "{combo}"\n'
                "end tell"
            )
            ok, detail = _run_command(["osascript", "-e", script])
            return {"ok": ok, "action": act, "detail": detail, "key_combo": combo}

        # type_text
        value = text or ""
        if not value.strip():
            return {"ok": False, "error": "text is required for type_text"}
        if len(value) > _MAX_TEXT_CHARS:
            return {"ok": False, "error": f"text exceeds {_MAX_TEXT_CHARS} characters"}

        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        script = (
            'tell application "System Events"\n'
            f'  keystroke "{escaped}"\n'
            "end tell"
        )
        ok, detail = _run_command(["osascript", "-e", script])
        return {"ok": ok, "action": act, "detail": detail, "chars": len(value)}

    return Tool(
        name="desktop_control",
        description=(
            "Control local macOS desktop actions: open an app, open a URL, send keystrokes, "
            "or type text into the focused app. Use carefully and only for explicit user requests."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "One of: open_app, open_url, keystroke, type_text",
                },
                "app": {"type": "string", "description": "App name for open_app (e.g., 'Safari')."},
                "url": {"type": "string", "description": "URL for open_url."},
                "key_combo": {"type": "string", "description": "Key combo for keystroke action."},
                "text": {"type": "string", "description": "Text to type for type_text action."},
            },
            "required": ["action"],
        },
        handler=_handle,
        tier="gated",
    )
