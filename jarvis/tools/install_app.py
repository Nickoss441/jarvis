"""Constrained macOS app installer helper.

This tool is intentionally strict:
- macOS only
- allowlist only
- supports dry_run and live modes
- prefers Homebrew casks, falls back to opening an official download URL
"""
from __future__ import annotations

import platform
import subprocess
from typing import Any, Callable

from . import Tool


_ALLOWED_APPS: dict[str, dict[str, str]] = {
    "arc": {
        "brew_cask": "arc",
        "download_url": "https://arc.net/download",
    },
    "spotify": {
        "brew_cask": "spotify",
        "download_url": "https://www.spotify.com/download",
    },
    "visual studio code": {
        "brew_cask": "visual-studio-code",
        "download_url": "https://code.visualstudio.com/Download",
    },
    "google chrome": {
        "brew_cask": "google-chrome",
        "download_url": "https://www.google.com/chrome/",
    },
    "slack": {
        "brew_cask": "slack",
        "download_url": "https://slack.com/downloads/mac",
    },
}


def _run_command(argv: list[str], timeout: int = 120) -> tuple[bool, str]:
    try:
        out = subprocess.run(  # noqa: S603
            argv,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return False, "command timed out"
    except FileNotFoundError:
        return False, "required executable not found"

    if out.returncode != 0:
        detail = (out.stderr or out.stdout or "command failed").strip()
        return False, detail[:800]

    detail = (out.stdout or "ok").strip()
    return True, detail[:800]


def _find_allowed_entry(app: str) -> tuple[str, dict[str, str]] | None:
    key = (app or "").strip().lower()
    if not key:
        return None
    if key in _ALLOWED_APPS:
        return key, _ALLOWED_APPS[key]

    # Accept exact cask alias values as user input.
    for app_key, entry in _ALLOWED_APPS.items():
        if key == entry.get("brew_cask", "").lower():
            return app_key, entry
    return None


def _normalize_install_payload(payload: dict[str, Any]) -> tuple[str, dict[str, str], str, bool] | None:
    app = str(payload.get("app") or "")
    resolved = _find_allowed_entry(app)
    if not resolved:
        return None

    app_key, entry = resolved
    selected_method = str(payload.get("method") or "auto").strip().lower()
    if selected_method not in {"auto", "brew", "url"}:
        return None
    open_after_download = bool(payload.get("open_after_download", True))
    return app_key, entry, selected_method, open_after_download


def dispatch_install_app(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = _normalize_install_payload(payload)
    if not normalized:
        return {
            "ok": False,
            "error": "invalid install_app payload",
        }

    app_key, entry, selected_method, open_after_download = normalized
    brew_cask = entry.get("brew_cask", "")
    download_url = entry.get("download_url", "")

    if platform.system() != "Darwin":
        return {
            "ok": False,
            "error": "install_app currently supports macOS only",
        }

    def _install_with_brew() -> tuple[bool, str]:
        if not brew_cask:
            return False, "no brew cask configured"
        ok, detail = _run_command(["brew", "--version"], timeout=15)
        if not ok:
            return False, detail
        ok, detail = _run_command(["brew", "install", "--cask", brew_cask], timeout=900)
        return ok, detail

    def _install_with_url() -> tuple[bool, str]:
        if not download_url:
            return False, "no download URL configured"
        ok, detail = _run_command(["open", download_url], timeout=30)
        if not ok:
            return False, detail
        message = "opened official download URL"
        if open_after_download:
            message += "; complete installer prompts to finish"
        return True, message

    if selected_method == "brew":
        ok, detail = _install_with_brew()
        return {
            "ok": ok,
            "status": "installed_with_brew" if ok else "install_failed",
            "app": app_key,
            "method": "brew",
            "detail": detail,
        }

    if selected_method == "url":
        ok, detail = _install_with_url()
        return {
            "ok": ok,
            "status": "opened_download_url" if ok else "install_failed",
            "app": app_key,
            "method": "url",
            "detail": detail,
        }

    # auto mode: prefer brew; fallback to URL.
    brew_ok, brew_detail = _install_with_brew()
    if brew_ok:
        return {
            "ok": True,
            "status": "installed_with_brew",
            "app": app_key,
            "method": "brew",
            "detail": brew_detail,
        }

    url_ok, url_detail = _install_with_url()
    return {
        "ok": url_ok,
        "status": "opened_download_url" if url_ok else "install_failed",
        "app": app_key,
        "method": "url",
        "detail": url_detail,
        "fallback_from": "brew",
        "brew_error": brew_detail,
    }


def make_install_app_tool(
    mode: str = "dry_run",
    request_approval: Callable[[str, dict[str, Any]], str] | None = None,
    get_approval: Callable[[str], dict[str, Any] | None] | None = None,
) -> Tool:
    """Build a gated app-install tool for sandbox phase workflows."""

    def _handle(
        app: str,
        method: str = "auto",
        open_after_download: bool = True,
        **_: Any,
    ) -> dict[str, Any]:
        payload = {
            "app": app,
            "method": method,
            "open_after_download": open_after_download,
        }

        normalized = _normalize_install_payload(payload)
        if not normalized:
            # Keep helpful allowlist feedback for users.
            if not _find_allowed_entry(str(app or "")):
                return {
                    "ok": False,
                    "error": "app is not in the allowlist",
                    "allowed_apps": sorted(_ALLOWED_APPS.keys()),
                }
            return {"ok": False, "error": "method must be one of: auto, brew, url"}

        app_key, entry, selected_method, _ = normalized

        if mode == "dry_run":
            return {
                "ok": True,
                "mode": "dry_run",
                "app": app_key,
                "method": selected_method,
                "plan": {
                    "brew_cask": entry.get("brew_cask", ""),
                    "download_url": entry.get("download_url", ""),
                },
            }

        if request_approval:
            approval_payload = {
                "app": app_key,
                "method": selected_method,
                "open_after_download": bool(open_after_download),
            }
            approval_id = request_approval("install_app", approval_payload)
            approval = get_approval(approval_id) if get_approval else None
            return {
                "status": "pending_approval",
                "approval_id": approval_id,
                "correlation_id": approval["correlation_id"] if approval else "",
                "kind": "install_app",
                "message": "install request queued for approval",
            }

        return dispatch_install_app(
            {
                "app": app_key,
                "method": selected_method,
                "open_after_download": bool(open_after_download),
            }
        )

    return Tool(
        name="install_app",
        description=(
            "Install allowlisted macOS apps. Uses Homebrew casks when available "
            "and falls back to opening the official download URL."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "app": {
                    "type": "string",
                    "description": "Allowlisted app name (e.g. arc, spotify, visual studio code).",
                },
                "method": {
                    "type": "string",
                    "description": "Install method: auto (default), brew, or url.",
                    "default": "auto",
                },
                "open_after_download": {
                    "type": "boolean",
                    "description": "When using URL mode, indicate manual installer completion is expected.",
                    "default": True,
                },
            },
            "required": ["app"],
        },
        handler=_handle,
        tier="gated",
    )
