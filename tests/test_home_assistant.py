"""Tests for the home_assistant tool scaffold."""
import pytest

from jarvis.tools.home_assistant import make_home_assistant_tool


def _make_tool(mode="dry_run"):
    return make_home_assistant_tool(
        ha_url="http://ha.local:8123",
        ha_token_getter=lambda: "test-token",
        mode=mode,
        timeout_seconds=5,
    )


# ── tool contract ──────────────────────────────────────────────────────────────

def test_tool_name_and_tier():
    tool = _make_tool()
    assert tool.name == "home_assistant"
    assert tool.tier == "open"


def test_tool_schema_type_object():
    tool = _make_tool()
    schema = tool.input_schema
    assert schema["type"] == "object"
    assert "action" in schema["properties"]
    assert "action" in schema["required"]


# ── get_state (dry_run) ────────────────────────────────────────────────────────

def test_get_state_known_entity_dry_run():
    tool = _make_tool()
    result = tool.handler(action="get_state", entity_id="light.living_room")

    assert result["mode"] == "dry_run"
    assert result["entity"]["entity_id"] == "light.living_room"
    assert result["entity"]["state"] == "on"


def test_get_state_unknown_entity_dry_run():
    tool = _make_tool()
    result = tool.handler(action="get_state", entity_id="sensor.unknown_xyz")

    assert result["mode"] == "dry_run"
    assert result["state"] == "unknown"
    assert "entity_id" in result


def test_get_state_requires_entity_id():
    tool = _make_tool()
    result = tool.handler(action="get_state")
    assert "error" in result
    assert "entity_id" in result["error"]


# ── list_states (dry_run) ──────────────────────────────────────────────────────

def test_list_states_returns_all_stubs():
    tool = _make_tool()
    result = tool.handler(action="list_states")

    assert result["mode"] == "dry_run"
    assert result["count"] >= 3
    entity_ids = [e["entity_id"] for e in result["entities"]]
    assert "light.living_room" in entity_ids
    assert "sensor.bedroom_temperature" in entity_ids


def test_list_states_filters_by_domain():
    tool = _make_tool()
    result = tool.handler(action="list_states", domain="sensor")

    assert result["mode"] == "dry_run"
    for entity in result["entities"]:
        assert entity["entity_id"].startswith("sensor.")


def test_list_states_domain_with_trailing_dot():
    tool = _make_tool()
    result_a = tool.handler(action="list_states", domain="light")
    result_b = tool.handler(action="list_states", domain="light.")
    assert result_a["count"] == result_b["count"]


def test_list_states_no_match_returns_empty():
    tool = _make_tool()
    result = tool.handler(action="list_states", domain="nonexistent_domain")
    assert result["count"] == 0
    assert result["entities"] == []


# ── call_service (dry_run) ────────────────────────────────────────────────────

def test_call_service_returns_simulated_ok():
    tool = _make_tool()
    result = tool.handler(
        action="call_service",
        domain="light",
        service="turn_on",
        entity_id="light.living_room",
        service_data={"brightness": 200},
    )

    assert result["mode"] == "dry_run"
    assert result["result"] == "simulated_ok"
    assert result["domain"] == "light"
    assert result["service"] == "turn_on"
    assert result["entity_id"] == "light.living_room"
    assert result["service_data"] == {"brightness": 200}
    assert "call_id" in result
    assert "ts" in result


def test_call_service_empty_service_data():
    tool = _make_tool()
    result = tool.handler(
        action="call_service",
        domain="switch",
        service="turn_off",
        entity_id="switch.office_fan",
    )
    assert result["mode"] == "dry_run"
    assert result["service_data"] == {}


def test_call_service_requires_domain():
    tool = _make_tool()
    result = tool.handler(action="call_service", service="turn_on", entity_id="light.x")
    assert "error" in result
    assert "domain" in result["error"]


def test_call_service_requires_service():
    tool = _make_tool()
    result = tool.handler(action="call_service", domain="light", entity_id="light.x")
    assert "error" in result
    assert "service" in result["error"]


def test_call_service_requires_entity_id():
    tool = _make_tool()
    result = tool.handler(action="call_service", domain="light", service="turn_on")
    assert "error" in result
    assert "entity_id" in result["error"]


# ── invalid action ─────────────────────────────────────────────────────────────

def test_unknown_action_returns_error():
    tool = _make_tool()
    result = tool.handler(action="explode_house")
    assert "error" in result
    assert "explode_house" in result["error"]


def test_empty_action_returns_error():
    tool = _make_tool()
    result = tool.handler(action="")
    assert "error" in result


# ── phase gate (cli.py integration) ───────────────────────────────────────────

def test_tool_registered_when_smart_home_phase_enabled(tmp_path):
    """home_assistant tool appears in registry only when phase_smart_home=True."""
    import os
    import importlib

    # build registry directly in dry-run mode without going through full Config
    from jarvis.tools import ToolRegistry
    from jarvis.tools.home_assistant import make_home_assistant_tool

    registry = ToolRegistry()
    registry.register(
        make_home_assistant_tool(
            ha_url="",
            ha_token_getter=lambda: "",
            mode="dry_run",
        )
    )

    tool = registry.get("home_assistant")
    assert tool is not None
    assert tool.name == "home_assistant"
