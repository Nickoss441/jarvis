import types

import pytest

from jarvis.cli import build_system_control_brain_from_config
from jarvis.config import Config


def _install_fake_anthropic(monkeypatch):
    fake_client = types.SimpleNamespace(messages=types.SimpleNamespace(create=lambda **_kwargs: None))

    def _make_client(api_key: str):
        return fake_client

    monkeypatch.setitem(
        __import__("sys").modules,
        "anthropic",
        types.SimpleNamespace(Anthropic=_make_client),
    )


def test_build_system_control_brain_registers_only_control_tools(tmp_path, monkeypatch):
    _install_fake_anthropic(monkeypatch)

    config = Config(
        anthropic_api_key="test-key",
        model="claude-sonnet-4-6",
        notes_dir=tmp_path / "notes",
        audit_db=tmp_path / "audit.db",
        conversation_store_path=tmp_path / "conversation.json",
        approval_db=tmp_path / "approvals.db",
        message_outbox=tmp_path / "outbox.jsonl",
        event_bus_db=tmp_path / "event-bus.db",
        user_name="Nick",
        phase_sandbox=True,
    )

    brain = build_system_control_brain_from_config(config)

    assert set(tool["name"] for tool in brain.tools.metadata()["tools"]) == {
        "desktop_control",
        "app_status",
        "app_list",
        "install_app",
        "uninstall_app",
    }
    assert "Jarvis System Control" in brain._system()


def test_build_system_control_brain_requires_sandbox_phase(tmp_path):
    config = Config(
        anthropic_api_key="test-key",
        model="claude-sonnet-4-6",
        notes_dir=tmp_path / "notes",
        audit_db=tmp_path / "audit.db",
        conversation_store_path=tmp_path / "conversation.json",
        approval_db=tmp_path / "approvals.db",
        message_outbox=tmp_path / "outbox.jsonl",
        event_bus_db=tmp_path / "event-bus.db",
        user_name="Nick",
        phase_sandbox=False,
    )

    with pytest.raises(ValueError, match="JARVIS_PHASE_SANDBOX"):
        build_system_control_brain_from_config(config)