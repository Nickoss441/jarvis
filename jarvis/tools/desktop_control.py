"""Desktop control tool for local macOS automation.

This tool is intentionally constrained and intended for local operator workflows.
It supports a small set of actions:
- active_window: inspect the current frontmost app/window
- focus_app: bring an app to the foreground by name
- close_window: close the current frontmost window
- open_app: launch or focus an app by name
- open_url: open a URL with the default handler
- open_chrome_url: open a URL specifically in Google Chrome
- keystroke: send a key combo using AppleScript System Events
- type_text: type plain text into the focused app

Register only when phase_sandbox is enabled.
"""
from __future__ import annotations

import base64
import platform
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from . import Tool

_MAX_TEXT_CHARS = 500
_VALID_ACTIONS = {"active_window", "focus_app", "close_window", "screenshot", "open_app", "open_url", "open_chrome_url", "keystroke", "type_text"}
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


def _capture_screenshot_png() -> bytes:
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as handle:
        screenshot_path = Path(handle.name)

    try:
        out = subprocess.run(  # noqa: S603
            ["screencapture", "-x", "-t", "png", str(screenshot_path)],
            capture_output=True,
            timeout=15,
        )
        if out.returncode != 0:
            msg = (out.stderr or out.stdout or b"command failed").decode("utf-8", errors="replace").strip()
            raise RuntimeError(msg[:800])
        return screenshot_path.read_bytes()
    finally:
        screenshot_path.unlink(missing_ok=True)


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

        if act == "active_window":
            script = (
                'tell application "System Events"\n'
                '  set frontApp to first application process whose frontmost is true\n'
                '  set appName to name of frontApp\n'
                '  set windowTitle to ""\n'
                '  try\n'
                '    if (count of windows of frontApp) > 0 then\n'
                '      set windowTitle to name of front window of frontApp\n'
                '    end if\n'
                '  end try\n'
                '  return appName & linefeed & windowTitle\n'
                'end tell'
            )
            ok, detail = _run_command(["osascript", "-e", script])
            if not ok:
                return {"ok": False, "action": act, "detail": detail}

            app_name = ""
            window_title = ""
            lines = detail.splitlines()
            if lines:
                app_name = lines[0].strip()
            if len(lines) >= 2:
                window_title = lines[1].strip()

            return {
                "ok": True,
                "action": act,
                "app": app_name,
                "window_title": window_title,
                "detail": detail,
            }

        if act == "open_app":
            app_name = app.strip()
            if not app_name:
                return {"ok": False, "error": "app is required for open_app"}
            ok, detail = _run_command(["open", "-a", app_name])
            return {"ok": ok, "action": act, "detail": detail, "app": app_name}

        if act == "focus_app":
            app_name = app.strip()
            if not app_name:
                return {"ok": False, "error": "app is required for focus_app"}
            script = f'tell application "{app_name}" to activate'
            ok, detail = _run_command(["osascript", "-e", script])
            return {"ok": ok, "action": act, "detail": detail, "app": app_name}

        if act == "close_window":
            script = (
                'tell application "System Events"\n'
                '  set frontApp to first application process whose frontmost is true\n'
                '  if (count of windows of frontApp) = 0 then\n'
                '    return "no-window"\n'
                '  end if\n'
                '  click button 1 of front window of frontApp\n'
                '  return name of frontApp\n'
                'end tell'
            )
            ok, detail = _run_command(["osascript", "-e", script])
            if ok and detail == "no-window":
                return {"ok": False, "action": act, "error": "no front window to close"}
            return {"ok": ok, "action": act, "detail": detail}

        if act == "screenshot":
            try:
                image_bytes = _capture_screenshot_png()
            except RuntimeError as exc:
                return {"ok": False, "action": act, "error": str(exc)}

            return {
                "ok": True,
                "action": act,
                "mime_type": "image/png",
                "image_base64": base64.b64encode(image_bytes).decode("ascii"),
                "byte_count": len(image_bytes),
            }

        if act in {"open_url", "open_chrome_url"}:
            target = url.strip()
            if not target:
                return {"ok": False, "error": f"url is required for {act}"}
            if not (target.startswith("http://") or target.startswith("https://") or target.startswith("file://")):
                return {"ok": False, "error": "url must start with http://, https://, or file://"}
            command = ["open", target]
            if act == "open_chrome_url":
                command = ["open", "-a", "Google Chrome", target]
            ok, detail = _run_command(command)
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
            "Control local macOS desktop actions: inspect the active window, focus an app, close the current window, "
            "take a screenshot, open an app, open a URL, open a URL in Google Chrome, send keystrokes, or type text into the focused app. Use carefully and only for explicit user requests."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "One of: active_window, focus_app, close_window, screenshot, open_app, open_url, open_chrome_url, keystroke, type_text",
                },
                "app": {"type": "string", "description": "App name for open_app or focus_app (e.g., 'Safari')."},
                "url": {"type": "string", "description": "URL for open_url or open_chrome_url."},
                "key_combo": {"type": "string", "description": "Key combo for keystroke action."},
                "text": {"type": "string", "description": "Text to type for type_text action."},
            },
            "required": ["action"],
        },
        handler=_handle,
        tier="gated",
    )
