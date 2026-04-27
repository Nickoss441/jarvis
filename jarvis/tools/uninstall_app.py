"""Remove an allowlisted macOS app with optional approval gating.

Supports dry_run and live modes:
  - dry_run: Returns a removal plan without taking action.
  - live: Queues approval request, then executes uninstall via dispatch callback.

Allowlisted apps: arc, spotify, visual studio code, google chrome, slack

Uninstall strategy:
  1. Attempt `brew uninstall --cask <app>` (most common case).
  2. Fall back to printing removal directions if brew fails.
"""
import json
import platform
import subprocess
from typing import Any, Callable

def make_uninstall_app_tool(
    mode: str = "live",
    request_approval: Callable[[str], str] | None = None,
    get_approval: Callable[[str], dict[str, Any] | None] | None = None,
) -> dict[str, Any]:
    """Create the uninstall_app tool.
    
    Args:
        mode: "dry_run" or "live".
        request_approval: Optional callback to request approval.
        get_approval: Optional callback to check approval status.
    
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

    def _run_command(cmd: list[str]) -> tuple[int, str, str]:
        """Run shell command, return (returncode, stdout, stderr)."""
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
            )
            return result.returncode, result.stdout.strip(), result.stderr.strip()
        except subprocess.TimeoutExpired:
            return 1, "", "command timed out"
        except (FileNotFoundError, OSError) as e:
            return 1, "", str(e)

    def _uninstall_app_live(app_name: str) -> dict[str, Any]:
        """Attempt actual macOS app removal."""
        entry = _find_allowed_entry(app_name)
        if not entry:
            return {"ok": False, "error": "app_not_allowlisted"}

        display_name = entry.get("display_name", app_name)
        brew_cask = entry.get("brew_cask", "")

        # Guard: macOS only
        if platform.system() != "Darwin":
            return {"ok": False, "error": "not_macos", "detail": f"uninstall_app only works on macOS, got {platform.system()}"}

        # Try brew uninstall
        returncode, stdout, stderr = _run_command(["brew", "uninstall", "--cask", brew_cask])
        
        if returncode == 0:
            return {
                "ok": True,
                "app": display_name,
                "method": "brew_uninstall",
                "status": "uninstalled",
            }
        
        # Brew failed; return fallback directions
        return {
            "ok": True,
            "app": display_name,
            "method": "manual",
            "status": "manual_removal_needed",
            "directions": f"Brew uninstall failed. To manually remove {display_name}:\n1. Open Applications folder\n2. Find {display_name}\n3. Drag to Trash\n4. Empty Trash\n\nBrew error: {stderr}",
        }

    def _uninstall_app_dry_run(app_name: str) -> dict[str, Any]:
        """Dry-run mode: return removal plan without taking action."""
        entry = _find_allowed_entry(app_name)
        if not entry:
            return {"ok": False, "error": "app_not_allowlisted"}

        display_name = entry.get("display_name", app_name)
        brew_cask = entry.get("brew_cask", "")

        return {
            "ok": True,
            "app": display_name,
            "method": "brew_uninstall",
            "status": "dry_run_plan",
            "plan": f"Would execute: brew uninstall --cask {brew_cask}",
        }

    def handler(app: str) -> dict[str, Any]:
        """Request app uninstallation (approval-gated in live mode).
        
        Args:
            app: App name (e.g., "spotify", "visual studio code").
        
        Returns:
            Dict with:
              - ok: True if query succeeded.
              - app: Display name of the app.
              - status: One of "dry_run_plan", "uninstalled", "manual_removal_needed", or error.
              - method: "brew_uninstall" or "manual".
              - error: Error code if ok=False.
        """
        if mode == "dry_run":
            return _uninstall_app_dry_run(app)
        else:  # live
            # Check if approval workflow is available
            if request_approval and get_approval:
                # Queue approval and return immediately with correlation ID
                prompt = f"Uninstall {_find_allowed_entry(app).get('display_name', app) if _find_allowed_entry(app) else app}?"
                approval_id = request_approval(prompt)
                return {
                    "ok": True,
                    "app": app,
                    "status": "approval_requested",
                    "approval_id": approval_id,
                }
            else:
                # No approval service; execute live
                return _uninstall_app_live(app)

    return {
        "name": "uninstall_app",
        "description": "Request uninstallation of an allowlisted macOS app (approval-gated).",
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


def dispatch_uninstall_app(mode: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Dispatch handler for approved uninstall_app requests.
    
    Called by ApprovalService after approval is confirmed.
    
    Args:
        mode: "dry_run" or "live".
        payload: {"app": "spotify", "approval_id": "..."}
    
    Returns:
        Dispatch result: {ok, app, status, method, ...}
    """
    app_name = payload.get("app", "")
    tool = make_uninstall_app_tool(mode=mode)
    handler = tool["handler"]
    return handler(app=app_name)
