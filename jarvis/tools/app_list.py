"""Tool to list all allowlisted macOS apps and their installation status.

Provides discovery and inventory of available apps that can be installed, uninstalled,
or status-checked via the app lifecycle tools.
"""
import platform
import subprocess
from typing import Any, TypedDict


class AppListResult(TypedDict):
    ok: bool
    apps: list[dict[str, Any]]
    count: int


ALLOWED_APPS = {
    "arc": {"label": "Arc", "bundle": "company.thebrowser.Browser"},
    "spotify": {"label": "Spotify", "bundle": "com.spotify.client"},
    "visual studio code": {"label": "Visual Studio Code", "bundle": "com.microsoft.VSCode"},
    "google chrome": {"label": "Google Chrome", "bundle": "com.google.Chrome"},
    "slack": {"label": "Slack", "bundle": "com.tinyspeck.slackmacgap"},
}


def make_app_list_tool(mode: str = "live") -> dict[str, Any]:
    """Factory for the app_list tool.

    Args:
        mode: "live" or "dry_run". In live mode, queries the system for installation
              status. In dry_run mode, returns mock data without system calls.

    Returns:
        Tool schema dict with handler.
    """

    def handler() -> AppListResult:
        """List all allowlisted apps and their installation status."""
        if platform.system() != "Darwin":
            return {
                "ok": False,
                "apps": [],
                "count": 0,
            }

        if mode == "dry_run":
            return _list_apps_dry_run()

        return _list_apps_live()

    return {
        "name": "app_list",
        "description": "List all allowlisted macOS apps and their installation status",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
        "handler": handler,
    }


def _list_apps_live() -> AppListResult:
    """Query the system for installation status of allowlisted apps."""
    if platform.system() != "Darwin":
        return {
            "ok": False,
            "apps": [],
            "count": 0,
        }

    apps = []

    for app_name, app_info in ALLOWED_APPS.items():
        result = _check_app_live(app_name)
        apps.append(result)

    return {
        "ok": True,
        "apps": apps,
        "count": len(apps),
    }


def _list_apps_dry_run() -> AppListResult:
    """Return mock status for all allowlisted apps."""
    apps = []

    for app_name, app_info in ALLOWED_APPS.items():
        apps.append({
            "name": app_name,
            "label": app_info["label"],
            "installed": False,
            "version": None,
        })

    return {
        "ok": True,
        "apps": apps,
        "count": len(apps),
    }


def _check_app_live(app_name: str) -> dict[str, Any]:
    """Check if a single app is installed and get its version.

    Args:
        app_name: Name of the app (e.g., "slack").

    Returns:
        Dict with app status and version.
    """
    app_info = ALLOWED_APPS.get(app_name, {})
    label = app_info.get("label", app_name)
    bundle = app_info.get("bundle", "")

    if not bundle:
        return {
            "name": app_name,
            "label": label,
            "installed": False,
            "version": None,
        }

    try:
        # Use mdfind to locate the app by bundle ID
        result = subprocess.run(
            ["mdfind", f"kMDItemCFBundleIdentifier == '{bundle}'"],
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode != 0 or not result.stdout.strip():
            return {
                "name": app_name,
                "label": label,
                "installed": False,
                "version": None,
            }

        # App found, now get version
        app_path = result.stdout.strip().split("\n")[0]
        version_result = subprocess.run(
            ["mdls", "-name", "kMDItemVersion", app_path],
            capture_output=True,
            text=True,
            timeout=5,
        )

        version = None
        if version_result.returncode == 0:
            # Parse "kMDItemVersion = "1.0.0"" format
            output = version_result.stdout.strip()
            if "=" in output:
                version_str = output.split("=", 1)[1].strip()
                version = version_str.strip('"')

        return {
            "name": app_name,
            "label": label,
            "installed": True,
            "version": version,
        }

    except (subprocess.TimeoutExpired, FileNotFoundError):
        return {
            "name": app_name,
            "label": label,
            "installed": False,
            "version": None,
        }
    except Exception:
        return {
            "name": app_name,
            "label": label,
            "installed": False,
            "version": None,
        }
