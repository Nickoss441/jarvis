"""Typed runtime-facing tool contract definitions."""
from dataclasses import dataclass
from typing import Any, Callable, Literal, TypeAlias


ToolTier: TypeAlias = Literal["open", "gated"]
ToolHandler: TypeAlias = Callable[..., Any]


@dataclass(frozen=True)
class RuntimeToolContract:
    """Canonical runtime tool definition used by the registry and brain loop."""

    name: str
    description: str
    input_schema: dict[str, Any]
    handler: ToolHandler
    tier: ToolTier = "open"

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("tool name must not be empty")
        if not self.description.strip():
            raise ValueError("tool description must not be empty")
        if not isinstance(self.input_schema, dict) or not self.input_schema:
            raise ValueError("tool input_schema must be a non-empty dict")
        if self.tier not in ("open", "gated"):
            raise ValueError("tool tier must be 'open' or 'gated'")

    def schema(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
        }
