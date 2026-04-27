"""Conversation memory.

Phase 1: in-process only — wiped on restart. Phase 2 will persist sessions
into a vector store for long-term recall.
"""
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Conversation:
    messages: list[dict[str, Any]] = field(default_factory=list)

    def add_user(self, text: str) -> None:
        self.messages.append({"role": "user", "content": text})

    def add_assistant(self, content: list[dict[str, Any]]) -> None:
        """`content` is the list-of-blocks form Anthropic's API expects."""
        self.messages.append({"role": "assistant", "content": content})

    def add_tool_results(self, tool_results: list[dict[str, Any]]) -> None:
        """Tool results are sent back as a `user` turn with `tool_result` blocks."""
        self.messages.append({"role": "user", "content": tool_results})

    def reset(self) -> None:
        self.messages = []
