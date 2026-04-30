"""Desktop control tool for local desktop automation.

This tool is intentionally constrained and intended for local operator workflows.
It supports a small set of actions:
- active_window: inspect the current frontmost app/window
- focus_app: bring an app to the foreground by name
- close_window: close the current frontmost window
- minimize_window: minimize the current frontmost window
- open_app: launch or focus an app by name
- open_url: open a URL with the default handler
- open_chrome_url: open a URL specifically in Google Chrome
- keystroke: send a key combo using AppleScript System Events or pyautogui
- type_text: type plain text into the focused app

Register only when phase_sandbox is enabled.
"""
from __future__ import annotations

import base64
import io
import os
import platform
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from . import Tool

_MAX_TEXT_CHARS = 500
_VALID_ACTIONS = {"active_window", "focus_app", "close_window", "minimize_window", "screenshot", "open_app", "open_url", "open_chrome_url", "keystroke", "type_text"}
_KEY_COMBO_PATTERN = re.compile(r"^[A-Za-z0-9+\-_ ]{1,60}$")


def _load_pyautogui() -> tuple[Any | None, str]:
    try:
        import pyautogui as _pyautogui
    except Exception as exc:  # noqa: BLE001
        return None, f"pyautogui unavailable: {exc}"
    return _pyautogui, ""


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


def _capture_screenshot_png_windows(pyautogui: Any) -> bytes:
    image = pyautogui.screenshot()
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


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

        os_name = platform.system()
        if os_name not in {"Darwin", "Windows"}:
            return {"ok": False, "error": "desktop_control currently supports macOS and Windows"}

        if act == "active_window":
            if os_name == "Windows":
                pyautogui, err = _load_pyautogui()
                if not pyautogui:
                    return {"ok": False, "action": act, "error": err}
                try:
                    window = pyautogui.getActiveWindow()
                    if window is None:
                        return {"ok": False, "action": act, "error": "no active window"}
                    title = str(getattr(window, "title", "") or "").strip()
                    return {
                        "ok": True,
                        "action": act,
                        "app": title,
                        "window_title": title,
                        "detail": title or "active-window",
                    }
                except Exception as exc:  # noqa: BLE001
                    return {"ok": False, "action": act, "error": f"active window lookup failed: {exc}"}

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
            if os_name == "Windows":
                try:
                    # Use `start` so named apps like "spotify" resolve via shell associations
                    subprocess.Popen(["cmd", "/c", "start", "", app_name], shell=False)  # noqa: S603
                    return {"ok": True, "action": act, "detail": "launched", "app": app_name}
                except Exception as exc:  # noqa: BLE001
                    return {"ok": False, "action": act, "error": f"failed to open app: {exc}", "app": app_name}
            ok, detail = _run_command(["open", "-a", app_name])
            return {"ok": ok, "action": act, "detail": detail, "app": app_name}

        if act == "focus_app":
            app_name = app.strip()
            if not app_name:
                return {"ok": False, "error": "app is required for focus_app"}
            if os_name == "Windows":
                return {"ok": False, "action": act, "error": "focus_app is currently supported on macOS only", "app": app_name}
            script = f'tell application "{app_name}" to activate'
            ok, detail = _run_command(["osascript", "-e", script])
            return {"ok": ok, "action": act, "detail": detail, "app": app_name}

        if act == "close_window":
            if os_name == "Windows":
                pyautogui, err = _load_pyautogui()
                if not pyautogui:
                    return {"ok": False, "action": act, "error": err}
                try:
                    pyautogui.hotkey("alt", "f4")
                    return {"ok": True, "action": act, "detail": "sent alt+f4"}
                except Exception as exc:  # noqa: BLE001
                    return {"ok": False, "action": act, "error": f"failed to close window: {exc}"}
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

        if act == "minimize_window":
            if os_name == "Windows":
                pyautogui, err = _load_pyautogui()
                if not pyautogui:
                    return {"ok": False, "action": act, "error": err}
                try:
                    pyautogui.hotkey("win", "down")
                    return {"ok": True, "action": act, "detail": "sent win+down"}
                except Exception as exc:  # noqa: BLE001
                    return {"ok": False, "action": act, "error": f"failed to minimize window: {exc}"}
            script = (
                'tell application "System Events"\n'
                '  set frontApp to first application process whose frontmost is true\n'
                '  if (count of windows of frontApp) = 0 then\n'
                '    return "no-window"\n'
                '  end if\n'
                '  set value of attribute "AXMinimized" of front window of frontApp to true\n'
                '  return name of frontApp\n'
                'end tell'
            )
            ok, detail = _run_command(["osascript", "-e", script])
            if ok and detail == "no-window":
                return {"ok": False, "action": act, "error": "no front window to minimize"}
            return {"ok": ok, "action": act, "detail": detail}

        if act == "screenshot":
            try:
                if os_name == "Windows":
                    pyautogui, err = _load_pyautogui()
                    if not pyautogui:
                        return {"ok": False, "action": act, "error": err}
                    image_bytes = _capture_screenshot_png_windows(pyautogui)
                else:
                    image_bytes = _capture_screenshot_png()
            except RuntimeError as exc:
                return {"ok": False, "action": act, "error": str(exc)}
            except Exception as exc:  # noqa: BLE001
                return {"ok": False, "action": act, "error": f"screenshot failed: {exc}"}

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
            if os_name == "Windows":
                if act == "open_chrome_url":
                    ok, detail = _run_command(["cmd", "/c", "start", "", "chrome", target])
                    return {"ok": ok, "action": act, "detail": detail, "url": target}
                try:
                    os.startfile(target)  # type: ignore[attr-defined]
                    return {"ok": True, "action": act, "detail": "opened", "url": target}
                except Exception as exc:  # noqa: BLE001
                    return {"ok": False, "action": act, "error": f"failed to open url: {exc}", "url": target}
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
            if os_name == "Windows":
                pyautogui, err = _load_pyautogui()
                if not pyautogui:
                    return {"ok": False, "action": act, "error": err}
                keys = [item.strip().lower() for item in re.split(r"[+\s]+", combo) if item.strip()]
                if not keys:
                    return {"ok": False, "action": act, "error": "key_combo produced no keys"}
                try:
                    pyautogui.hotkey(*keys)
                    return {"ok": True, "action": act, "detail": "hotkey sent", "key_combo": combo}
                except Exception as exc:  # noqa: BLE001
                    return {"ok": False, "action": act, "error": f"failed to send hotkey: {exc}", "key_combo": combo}
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

        if os_name == "Windows":
            pyautogui, err = _load_pyautogui()
            if not pyautogui:
                return {"ok": False, "action": act, "error": err}
            try:
                pyautogui.write(value, interval=0.02)
                return {"ok": True, "action": act, "detail": "text typed", "chars": len(value)}
            except Exception as exc:  # noqa: BLE001
                return {"ok": False, "action": act, "error": f"failed to type text: {exc}"}

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
            "Control local desktop actions (macOS/Windows): inspect the active window, focus an app, close the current window, "
            "minimize the current window, take a screenshot, open an app, open a URL, open a URL in Google Chrome, send keystrokes, or type text into the focused app. Use carefully and only for explicit user requests."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "One of: active_window, focus_app, close_window, minimize_window, screenshot, open_app, open_url, open_chrome_url, keystroke, type_text",
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
