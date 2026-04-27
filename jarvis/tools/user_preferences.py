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

        if normalized_action == "store_contact_address":
            if not isinstance(patch, dict):
                return {
                    "ok": False,
                    "action": "store_contact_address",
                    "error": "patch must be an object",
                }

            contact = patch.get("contact")
            address = patch.get("address")
            merged_patch: dict[str, dict[str, Any]] = {}
            if contact is not None:
                if not isinstance(contact, dict):
                    return {
                        "ok": False,
                        "action": "store_contact_address",
                        "error": "contact must be an object",
                    }
                merged_patch["contact"] = contact
            if address is not None:
                if not isinstance(address, dict):
                    return {
                        "ok": False,
                        "action": "store_contact_address",
                        "error": "address must be an object",
                    }
                merged_patch["address"] = address

            if not merged_patch:
                return {
                    "ok": False,
                    "action": "store_contact_address",
                    "error": "patch must include contact and/or address",
                }

            try:
                data = store.update(merged_patch)
            except ValueError as exc:
                return {
                    "ok": False,
                    "action": "store_contact_address",
                    "error": str(exc),
                }
            return {
                "ok": True,
                "action": "store_contact_address",
                "data": data,
            }

        return {
            "ok": False,
            "error": "unknown action",
            "action": normalized_action,
            "allowed_actions": ["get", "update", "store_contact_address", "reset"],
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
                    "description": "One of: get, update, store_contact_address, reset",
                    "default": "get",
                },
                "patch": {
                    "type": "object",
                    "description": (
                        "Partial preference update keyed by section: profile, "
                        "contact, address, communication. For store_contact_address, include "
                        "contact and/or address sub-objects."
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
