import pytest

from jarvis.runtime import RuntimeToolContract
from jarvis.tools import Tool, ToolRegistry


def test_runtime_tool_contract_validates_and_exports_schema():
    tool = RuntimeToolContract(
        name="demo",
        description="Demo tool",
        input_schema={"type": "object", "properties": {}},
        handler=lambda: {"ok": True},
        tier="open",
    )

    assert tool.name == "demo"
    assert tool.tier == "open"
    assert tool.schema() == {
        "name": "demo",
        "description": "Demo tool",
        "input_schema": {"type": "object", "properties": {}},
    }


def test_runtime_tool_contract_rejects_invalid_tier():
    with pytest.raises(ValueError, match="tool tier"):
        RuntimeToolContract(
            name="demo",
            description="Demo tool",
            input_schema={"type": "object", "properties": {}},
            handler=lambda: {"ok": True},
            tier="invalid",  # type: ignore[arg-type]
        )


def test_tools_public_alias_uses_runtime_contract():
    tool = Tool(
        name="demo",
        description="Demo tool",
        input_schema={"type": "object", "properties": {}},
        handler=lambda: {"ok": True},
        tier="gated",
    )

    assert isinstance(tool, RuntimeToolContract)
    assert tool.tier == "gated"


def test_tool_registry_schemas_use_contract_schema_export():
    registry = ToolRegistry()
    registry.register(
        Tool(
            name="demo",
            description="Demo tool",
            input_schema={"type": "object", "properties": {"x": {"type": "string"}}},
            handler=lambda x: {"echo": x},
        )
    )

    assert registry.schemas() == [
        {
            "name": "demo",
            "description": "Demo tool",
            "input_schema": {"type": "object", "properties": {"x": {"type": "string"}}},
        }
    ]


def test_tool_registry_can_filter_by_tier_and_export_metadata():
    registry = ToolRegistry()
    registry.register(
        Tool(
            name="open-demo",
            description="Open demo tool",
            input_schema={"type": "object", "properties": {}},
            handler=lambda: {"ok": True},
            tier="open",
        )
    )
    registry.register(
        Tool(
            name="gated-demo",
            description="Gated demo tool",
            input_schema={"type": "object", "properties": {}},
            handler=lambda: {"ok": True},
            tier="gated",
        )
    )

    assert [tool.name for tool in registry.by_tier("open")] == ["open-demo"]
    assert [tool.name for tool in registry.by_tier("gated")] == ["gated-demo"]
    assert registry.metadata() == {
        "total": 2,
        "open_count": 1,
        "gated_count": 1,
        "tools": [
            {
                "name": "open-demo",
                "description": "Open demo tool",
                "tier": "open",
            },
            {
                "name": "gated-demo",
                "description": "Gated demo tool",
                "tier": "gated",
            },
        ],
    }
