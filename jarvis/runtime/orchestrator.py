"""Helpers for orchestrating a single agent runtime turn."""
from typing import Any, Iterable

from .turn import RuntimeTurnContext


class RuntimeOrchestrator:
    """Small coordination helper for the current brain loop.

    This package is the landing zone for future runtime-stage extraction.
    For now it centralizes turn state and common response shaping without
    changing the public behavior of the CLI or tests.
    """

    def __init__(self, max_iterations: int):
        self.max_iterations = max_iterations

    def start_turn(self, user_input: str, correlation_id: str) -> RuntimeTurnContext:
        return RuntimeTurnContext(
            user_input=user_input,
            correlation_id=correlation_id,
            max_iterations=self.max_iterations,
        )

    @staticmethod
    def final_text_from_blocks(blocks: Iterable[Any]) -> str:
        text = "".join(
            block.text for block in blocks if getattr(block, "type", None) == "text"
        ).strip()
        return text or "(no text response)"
