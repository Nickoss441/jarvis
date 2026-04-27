"""Conversation memory.

Phase 1: in-process only — wiped on restart. Phase 2 adds a lightweight
file-backed store for long-term recall across restarts.
"""
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .manifest import (
    decrypt_manifest_payload,
    encrypt_manifest_payload,
    is_encrypted_manifest_payload,
)


@dataclass
class Conversation:
    messages: list[dict[str, Any]] = field(default_factory=list)
    storage_path: Path | None = None

    def __post_init__(self) -> None:
        if self.storage_path is None:
            return
        try:
            payload = json.loads(self.storage_path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return
        except (OSError, json.JSONDecodeError):
            self.messages = []
            return

        if isinstance(payload, list) and all(isinstance(item, dict) for item in payload):
            self.messages = payload
        else:
            self.messages = []

    def _persist(self) -> None:
        if self.storage_path is None:
            return
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.storage_path.write_text(json.dumps(self.messages), encoding="utf-8")

    def add_user(self, text: str) -> None:
        self.messages.append({"role": "user", "content": text})
        self._persist()

    def add_assistant(self, content: list[dict[str, Any]]) -> None:
        """`content` is the list-of-blocks form Anthropic's API expects."""
        self.messages.append({"role": "assistant", "content": content})
        self._persist()

    def add_tool_results(self, tool_results: list[dict[str, Any]]) -> None:
        """Tool results are sent back as a `user` turn with `tool_result` blocks."""
        self.messages.append({"role": "user", "content": tool_results})
        self._persist()

    def reset(self) -> None:
        self.messages = []
        self._persist()


_PREFERENCE_SECTIONS = {
    "profile",
    "contact",
    "address",
    "communication",
}


def _merge_nested_dict(base: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge_nested_dict(merged[key], value)
        else:
            merged[key] = value
    return merged


@dataclass
class UserPreferencesStore:
    storage_path: Path
    encryption_secret: str = ""
    data: dict[str, dict[str, Any]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        try:
            payload = json.loads(self.storage_path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            self.data = {}
            return
        except (OSError, json.JSONDecodeError):
            self.data = {}
            return

        normalized = payload
        if self.encryption_secret and is_encrypted_manifest_payload(payload):
            try:
                normalized = decrypt_manifest_payload(payload, self.encryption_secret)
            except ValueError:
                self.data = {}
                return

        if not isinstance(normalized, dict):
            self.data = {}
            return

        self.data = {
            str(key): value
            for key, value in normalized.items()
            if isinstance(key, str) and isinstance(value, dict)
        }

    def _persist(self) -> None:
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        if self.encryption_secret:
            envelope = encrypt_manifest_payload(self.data, self.encryption_secret)
            self.storage_path.write_text(json.dumps(envelope), encoding="utf-8")
            return
        self.storage_path.write_text(json.dumps(self.data), encoding="utf-8")

    def update(self, patch: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
        unknown_sections = sorted(set(patch) - _PREFERENCE_SECTIONS)
        if unknown_sections:
            raise ValueError(f"unknown preference section: {', '.join(unknown_sections)}")

        merged = dict(self.data)
        for section, values in patch.items():
            if not isinstance(values, dict):
                raise ValueError(f"preference section '{section}' must be an object")
            merged[section] = _merge_nested_dict(merged.get(section, {}), values)

        self.data = merged
        self._persist()
        return self.data

    def reset(self) -> None:
        self.data = {}
        self._persist()
