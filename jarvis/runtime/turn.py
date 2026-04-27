"""Turn-scoped runtime state for the agent loop."""
from dataclasses import dataclass, field
from typing import Any


@dataclass
class RuntimeTurnContext:
    """Mutable state tracked across a single conversational turn."""

    user_input: str
    correlation_id: str
    max_iterations: int
    iteration: int = 0
    tool_results: list[dict[str, Any]] = field(default_factory=list)

    def advance_iteration(self) -> int:
        self.iteration += 1
        return self.iteration

    def add_tool_result(self, tool_use_id: str | None, result: Any) -> dict[str, Any]:
        block = {
            "type": "tool_result",
            "tool_use_id": tool_use_id,
            "content": str(result),
        }
        self.tool_results.append(block)
        return block

    @property
    def exhausted(self) -> bool:
        return self.iteration >= self.max_iterations
