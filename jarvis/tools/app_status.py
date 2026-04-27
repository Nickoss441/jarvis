"""Check whether an app is installed and detect its version.

Supports dry_run and live modes:
  - dry_run: Returns mock status for allowlisted apps.
  - live: Queries the macOS system to detect installation and version.

Allowlisted apps: arc, spotify, visual studio code, google chrome, slack
"""
import json
import platform
import subprocess
from typing import Any, Callable

def make_app_status_tool(
    mode: str = "live",
    request_approval: Callable[[str], str] | None = None,
    get_approval: Callable[[str], dict[str, Any] | None] | None = None,
) -> dict[str, Any]:
    """Create the app_status tool.
    
    Args:
        mode: "dry_run" or "live".
        request_approval: Optional callback to request approval (unused for status, provided for consistency).
        get_approval: Optional callback to get approval status (unused for status, provided for consistency).
    
    Returns:
        Tool schema dict with handler.
    """
    
    ALLOWLISTED_APPS = {
        "arc": {
            "bundle_id": "company.thebrowser.Browser",
            "display_name": "Arc",
            "brew_cask": "arc",
        },
        "spotify": {
            "bundle_id": "com.spotify.client",
            "display_name": "Spotify",
            "brew_cask": "spotify",
        },
        "visual studio code": {
            "bundle_id": "com.microsoft.VSCode",
            "display_name": "Visual Studio Code",
            "brew_cask": "visual-studio-code",
        },
        "google chrome": {
            "bundle_id": "com.google.Chrome",
            "display_name": "Google Chrome",
            "brew_cask": "google-chrome",
        },
        "slack": {
            "bundle_id": "com.tinyspeck.slackmacgap",
            "display_name": "Slack",
            "brew_cask": "slack",
        },
    }

    def _find_allowed_entry(app_name: str) -> dict[str, str] | None:
        """Find allowlist entry by app_name (case-insensitive)."""
        for key, entry in ALLOWLISTED_APPS.items():
            if key.lower() == app_name.lower():
                return entry
        return None

    def _run_command(cmd: list[str]) -> str:
        """Run shell command, return stripped stdout or empty string on error."""
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.stdout.strip()
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            return ""

    def _check_app_live(app_name: str) -> dict[str, Any]:
        """Check actual macOS system for app installation and version."""
        entry = _find_allowed_entry(app_name)
        if not entry:
            return {"ok": False, "error": "app_not_allowlisted"}

        display_name = entry.get("display_name", app_name)
        bundle_id = entry.get("bundle_id", "")

        # Guard: macOS only
        if platform.system() != "Darwin":
            return {"ok": False, "error": "not_macos", "detail": f"app_status only works on macOS, got {platform.system()}"}

        # Check installation via mdfind on bundle ID
        mdfind_result = _run_command(["mdfind", f"kMDItemCFBundleIdentifier == '{bundle_id}'"])
        if not mdfind_result:
            return {
                "ok": True,
                "app": display_name,
                "installed": False,
                "version": None,
            }

        # App is installed; try to get version
        app_path = mdfind_result.split("\n")[0] if mdfind_result else None
        version = None
        if app_path:
            # Try to read version via mdls
            version_result = _run_command([
                "mdls",
                "-name", "kMDItemVersion",
                "-raw",
                app_path,
            ])
            if version_result and version_result != "(null)":
                version = version_result

        return {
            "ok": True,
            "app": display_name,
            "installed": True,
            "version": version,
        }

    def _check_app_dry_run(app_name: str) -> dict[str, Any]:
        """Dry-run mode: return mock status for allowlisted apps."""
        entry = _find_allowed_entry(app_name)
        if not entry:
            return {"ok": False, "error": "app_not_allowlisted"}

        display_name = entry.get("display_name", app_name)
        return {
            "ok": True,
            "app": display_name,
            "installed": True,
            "version": "1.0.0 (dry-run mock)",
        }

    def handler(app: str) -> dict[str, Any]:
        """Check app installation status.
        
        Args:
            app: App name (e.g., "spotify", "visual studio code").
        
        Returns:
            Dict with:
              - ok: True if query succeeded.
              - app: Display name of the app.
              - installed: True if app is installed.
              - version: Version string if installed, else None.
              - error: Error code if ok=False (e.g., "app_not_allowlisted", "not_macos").
        """
        if mode == "dry_run":
            return _check_app_dry_run(app)
        else:  # live
            return _check_app_live(app)

    return {
        "name": "app_status",
        "description": "Check if an allowlisted macOS app is installed and detect its version.",
        "input_schema": {
            "type": "object",
            "properties": {
                "app": {
                    "type": "string",
                    "description": "App name (e.g., 'spotify', 'visual studio code', 'google chrome', 'slack', 'arc').",
                },
            },
            "required": ["app"],
        },
        "handler": handler,
    }
