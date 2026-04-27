"""Tool registry backed by the runtime tool contract.

The public `Tool` export remains available for current tool modules, while the
canonical contract now lives under `jarvis.runtime`.
"""
from typing import Any

from ..runtime import RuntimeToolContract, ToolTier


Tool = RuntimeToolContract


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, RuntimeToolContract] = {}

    def register(self, tool: RuntimeToolContract | dict[str, Any]) -> None:
        # Backward compatibility: accept legacy dict-based tool definitions.
        if isinstance(tool, dict):
            tool = RuntimeToolContract(
                name=str(tool.get("name", "")),
                description=str(tool.get("description", "")),
                input_schema=tool.get("input_schema", {}),
                handler=tool.get("handler"),
                tier=tool.get("tier", "open"),
            )
        self._tools[tool.name] = tool

    def get(self, name: str) -> RuntimeToolContract | None:
        return self._tools.get(name)

    def all(self) -> list[RuntimeToolContract]:
        return list(self._tools.values())

    def by_tier(self, tier: ToolTier) -> list[RuntimeToolContract]:
        return [tool for tool in self._tools.values() if tool.tier == tier]

    def metadata(self) -> dict[str, Any]:
        tools = [
            {
                "name": tool.name,
                "description": tool.description,
                "tier": tool.tier,
            }
            for tool in self._tools.values()
        ]
        return {
            "total": len(tools),
            "open_count": len(self.by_tier("open")),
            "gated_count": len(self.by_tier("gated")),
            "tools": tools,
        }

    def schemas(self) -> list[dict[str, Any]]:
        """Tool list in Anthropic's tool-use format."""
        return [t.schema() for t in self._tools.values()]
