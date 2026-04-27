"""User preferences tool.

Provides a small structured surface for the model to persist/retrieve stable
user profile/contact/address/communication preferences.
"""
from pathlib import Path
from typing import Any

from ..memory import UserPreferencesStore
from . import Tool


def make_user_preferences_tool(storage_path: Path, manifest_secret: str = "") -> Tool:
    store = UserPreferencesStore(
        storage_path=storage_path,
        encryption_secret=(manifest_secret or "").strip(),
    )

    def handler(action: str = "get", patch: dict[str, dict[str, Any]] | None = None) -> dict[str, Any]:
        normalized_action = str(action or "get").strip().lower()

        if normalized_action == "get":
            return {"ok": True, "action": "get", "data": store.data}

        if normalized_action == "reset":
            store.reset()
            return {"ok": True, "action": "reset", "data": store.data}

        if normalized_action == "update":
            if not isinstance(patch, dict):
                return {
                    "ok": False,
                    "action": "update",
                    "error": "patch must be an object",
                }
            try:
                data = store.update(patch)
            except ValueError as exc:
                return {"ok": False, "action": "update", "error": str(exc)}
            return {"ok": True, "action": "update", "data": data}

        return {
            "ok": False,
            "error": "unknown action",
            "action": normalized_action,
            "allowed_actions": ["get", "update", "reset"],
        }

    return Tool(
        name="user_preferences",
        description=(
            "Read and update structured user preferences for profile, contact, "
            "address, and communication settings."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "One of: get, update, reset",
                    "default": "get",
                },
                "patch": {
                    "type": "object",
                    "description": (
                        "Partial preference update keyed by section: profile, "
                        "contact, address, communication."
                    ),
                    "additionalProperties": {
                        "type": "object",
                    },
                },
            },
        },
        handler=handler,
        tier="open",
    )
