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
    react_cycles: list[dict[str, Any]] = field(default_factory=list)
    _current_react_cycle_index: int | None = field(default=None, init=False, repr=False)

    def advance_iteration(self) -> int:
        self.iteration += 1
        return self.iteration

    def begin_react_cycle(self) -> dict[str, Any]:
        cycle = {
            "iteration": self.iteration,
            "thought": "",
            "actions": [],
            "observations": [],
            "final_text": "",
            "completed": False,
        }
        self.react_cycles.append(cycle)
        self._current_react_cycle_index = len(self.react_cycles) - 1
        return cycle

    def _current_react_cycle(self) -> dict[str, Any]:
        if self._current_react_cycle_index is None:
            return self.begin_react_cycle()
        return self.react_cycles[self._current_react_cycle_index]

    def record_thought(self, thought: str) -> dict[str, Any]:
        cycle = self._current_react_cycle()
        normalized = thought.strip()
        if not normalized:
            return cycle
        if cycle["thought"]:
            cycle["thought"] = f"{cycle['thought']}\n{normalized}"
        else:
            cycle["thought"] = normalized
        return cycle

    def record_action(
        self,
        tool_name: str,
        args: dict[str, Any],
        tool_use_id: str | None = None,
    ) -> dict[str, Any]:
        cycle = self._current_react_cycle()
        action = {
            "tool_name": tool_name,
            "tool_use_id": tool_use_id,
            "args": args,
        }
        cycle["actions"].append(action)
        return action

    def record_observation(
        self,
        tool_name: str,
        result: Any,
        tool_use_id: str | None = None,
    ) -> dict[str, Any]:
        cycle = self._current_react_cycle()
        observation = {
            "tool_name": tool_name,
            "tool_use_id": tool_use_id,
            "result": result,
        }
        cycle["observations"].append(observation)
        return observation

    def complete_react_cycle(self, final_text: str = "") -> dict[str, Any]:
        cycle = self._current_react_cycle()
        cycle["completed"] = True
        if final_text.strip():
            cycle["final_text"] = final_text.strip()
        return cycle

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
