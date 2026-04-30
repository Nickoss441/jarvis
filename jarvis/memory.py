"""Conversation memory.

Phase 1: in-process only — wiped on restart. Phase 2 adds a lightweight
file-backed store for long-term recall across restarts.
"""
import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_log = logging.getLogger(__name__)

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
        except (OSError, json.JSONDecodeError) as exc:
            _log.warning("conversation history at %s is corrupt — resetting: %s", self.storage_path, exc)
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
        self.messages.append({"role": "user", "content": text, "ts": int(time.time() * 1000)})
        self._persist()

    def add_assistant(self, content: list[dict[str, Any]]) -> None:
        """`content` is the list-of-blocks form Anthropic's API expects."""
        self.messages.append({"role": "assistant", "content": content, "ts": int(time.time() * 1000)})
        self._persist()

    def add_tool_results(self, tool_results: list[dict[str, Any]]) -> None:
        """Tool results are sent back as a `user` turn with `tool_result` blocks."""
        self.messages.append({"role": "user", "content": tool_results, "ts": int(time.time() * 1000)})
        self._persist()

    def annotate_last_assistant(self, **metadata: Any) -> bool:
        for idx in range(len(self.messages) - 1, -1, -1):
            msg = self.messages[idx]
            if msg.get("role") != "assistant":
                continue
            msg.update(metadata)
            self._persist()
            return True
        return False

    def overwrite_last_user_text(self, text: str) -> bool:
        """Replace the most recent plain user text message in-place."""
        replacement = (text or "").strip()
        if not replacement:
            return False
        for idx in range(len(self.messages) - 1, -1, -1):
            msg = self.messages[idx]
            if msg.get("role") != "user":
                continue
            content = msg.get("content")
            if isinstance(content, str):
                msg["content"] = replacement
                self._persist()
                return True
            if isinstance(content, list):
                text_blocks = [
                    block for block in content
                    if isinstance(block, dict) and block.get("type") == "text"
                ]
                if not text_blocks:
                    continue
                text_blocks[0]["text"] = replacement
                for block in text_blocks[1:]:
                    block["text"] = ""
                self._persist()
                return True
        return False

    def overwrite_last_assistant_text(self, text: str) -> bool:
        """Replace the most recent assistant text block content in-place."""
        replacement = (text or "").strip()
        if not replacement:
            return False
        for idx in range(len(self.messages) - 1, -1, -1):
            msg = self.messages[idx]
            if msg.get("role") != "assistant":
                continue
            content = msg.get("content")
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        block["text"] = replacement
                        self._persist()
                        return True
                msg["content"] = [{"type": "text", "text": replacement}]
                self._persist()
                return True
            if isinstance(content, str):
                msg["content"] = replacement
                self._persist()
                return True
            msg["content"] = [{"type": "text", "text": replacement}]
            self._persist()
            return True
        return False

    def reset(self) -> None:
        self.messages = []
        self._persist()


    def trimmed_for_context(self, max_messages: int = 20) -> list[dict[str, Any]]:
        """Return last max_messages with strict tool_use/tool_result pairing enforced."""
        def _tool_use_ids(msg: dict) -> list[str]:
            content = msg.get("content", [])
            if not isinstance(content, list):
                return []
            return [b["id"] for b in content if isinstance(b, dict) and b.get("type") == "tool_use" and "id" in b]

        def _tool_result_ids(msg: dict) -> set[str]:
            content = msg.get("content", [])
            if not isinstance(content, list):
                return set()
            return {b["tool_use_id"] for b in content if isinstance(b, dict) and b.get("type") == "tool_result" and "tool_use_id" in b}

        msgs = list(self.messages[-max_messages:])
        changed = True
        while changed:
            changed = False
            clean: list[dict] = []
            i = 0
            while i < len(msgs):
                m = msgs[i]
                tool_ids = _tool_use_ids(m) if m.get("role") == "assistant" else []
                if tool_ids:
                    next_m = msgs[i + 1] if i + 1 < len(msgs) else None
                    result_ids = _tool_result_ids(next_m) if next_m and next_m.get("role") == "user" else set()
                    if all(tid in result_ids for tid in tool_ids) and next_m is not None:
                        clean.append(m)
                        clean.append(next_m)
                        i += 2
                    else:
                        changed = True
                        if next_m and next_m.get("role") == "user" and result_ids:
                            i += 2
                        else:
                            i += 1
                else:
                    clean.append(m)
                    i += 1
            msgs = clean
        return msgs[-max_messages:]

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
