"""Contract tests for the default tool registry."""
from pathlib import Path
from typing import Any

import pytest

from jarvis.config import Config
from jarvis.policy import Policy
import jarvis.cli as cli


class _FakeApprovalStore:
    def __init__(self):
        self._rows: dict[str, dict[str, str]] = {}

    def put(self, approval_id: str, correlation_id: str) -> None:
        self._rows[approval_id] = {"correlation_id": correlation_id}

    def get(self, _approval_id: str):
        return self._rows.get(_approval_id)


class _FakeApprovalService:
    def __init__(self, _config: Config):
        self.store = _FakeApprovalStore()
        self._counter = 0

    def request(self, *_args: Any, **_kwargs: Any) -> str:
        self._counter += 1
        approval_id = f"approval-id-{self._counter}"
        self.store.put(approval_id, f"corr-{self._counter}")
        return approval_id


class _FakeBrain:
    def __init__(self, _config, _audit, _policy, tools):
        self.tools = tools


def _build_test_config(tmp_path: Path) -> Config:
    return Config(
        anthropic_api_key="test-key",
        model="claude-sonnet-4-6",
        notes_dir=tmp_path / "notes",
        audit_db=tmp_path / "audit.db",
        user_name="Nick",
        approval_db=tmp_path / "approvals.db",
        calendar_ics=tmp_path / "calendar.ics",
        event_bus_db=tmp_path / "event-bus.db",
        dropzone_dir=tmp_path / "dropzone",
        mail_drafts_path=tmp_path / "mail-drafts.jsonl",
        message_outbox=tmp_path / "message-outbox.jsonl",
        calls_log_path=tmp_path / "calls-log.jsonl",
        payments_ledger=tmp_path / "payments-ledger.jsonl",
        trades_log=tmp_path / "trades-log.jsonl",
    )


def test_default_registry_tools_expose_object_input_schemas(tmp_path, monkeypatch) -> None:
    config = _build_test_config(tmp_path)

    monkeypatch.setattr(cli.Config, "from_env", classmethod(lambda cls: config))
    monkeypatch.setattr(cli.Policy, "from_file", classmethod(lambda cls, *_args, **_kwargs: Policy(rules={})))
    monkeypatch.setattr(cli, "ApprovalService", _FakeApprovalService)
    monkeypatch.setattr(cli, "Brain", _FakeBrain)

    brain = cli.build_brain()
    tools = brain.tools.all()

    assert tools
    names = {tool.name for tool in tools}
    assert "weather_now" in names
    assert "route_eta" in names
    assert "location_current" in names
    assert "user_preferences" in names
    assert "weather_here" in names
    assert "eta_to" in names
    for tool in tools:
        schema = tool.schema()
        assert schema["name"] == tool.name
        assert isinstance(schema["input_schema"], dict)


def test_default_registry_includes_desktop_tools_when_sandbox_enabled(tmp_path, monkeypatch) -> None:
    """Verify sandbox desktop and vision helpers are registered when sandbox phase is enabled."""
    config = _build_test_config(tmp_path)
    config.phase_sandbox = True

    monkeypatch.setattr(cli.Config, "from_env", classmethod(lambda cls: config))
    monkeypatch.setattr(cli.Policy, "from_file", classmethod(lambda cls, *_args, **_kwargs: Policy(rules={})))
    monkeypatch.setattr(cli, "ApprovalService", _FakeApprovalService)
    monkeypatch.setattr(cli, "Brain", _FakeBrain)

    brain = cli.build_brain()
    tools = brain.tools.all()
    names = {tool.name for tool in tools}

    assert "desktop_control" in names
    assert "vision_observe" in names
    assert "install_app" in names
    assert "app_status" in names
    assert "uninstall_app" in names


def test_registry_includes_desktop_control_when_sandbox_enabled(tmp_path, monkeypatch) -> None:
    config = _build_test_config(tmp_path)
    config.phase_sandbox = True

    monkeypatch.setattr(cli.Config, "from_env", classmethod(lambda cls: config))
    monkeypatch.setattr(cli.Policy, "from_file", classmethod(lambda cls, *_args, **_kwargs: Policy(rules={})))
    monkeypatch.setattr(cli, "ApprovalService", _FakeApprovalService)
    monkeypatch.setattr(cli, "Brain", _FakeBrain)

    brain = cli.build_brain()
    names = {tool.name for tool in brain.tools.all()}

    assert "shell_run" in names
    assert "file_write" in names
    assert "desktop_control" in names
    assert "vision_observe" in names
    assert "install_app" in names


@pytest.mark.parametrize(
    ("tool_name", "payload", "required_fields"),
    [
        (
            "message_send",
            {"channel": "email", "recipient": "user@example.com", "body": "hello"},
            ["channel", "recipient", "body"],
        ),
        (
            "call_phone",
            {"phone_number": "+14155552671", "message": "hello"},
            ["phone_number", "message"],
        ),
        (
            "payments",
            {"amount": 12.5, "currency": "USD", "recipient": "acct_123"},
            [],
        ),
        (
            "trade",
            {"instrument": "AAPL", "side": "buy", "size": 1, "rationale": "test"},
            ["instrument", "side", "size", "rationale"],
        ),
    ],
)
def test_default_registry_gated_tool_schema_and_handler_contract(
    tmp_path,
    monkeypatch,
    tool_name,
    payload,
    required_fields,
) -> None:
    config = _build_test_config(tmp_path)

    monkeypatch.setattr(cli.Config, "from_env", classmethod(lambda cls: config))
    monkeypatch.setattr(cli.Policy, "from_file", classmethod(lambda cls, *_args, **_kwargs: Policy(rules={})))
    monkeypatch.setattr(cli, "ApprovalService", _FakeApprovalService)
    monkeypatch.setattr(cli, "Brain", _FakeBrain)

    brain = cli.build_brain()
    tool = brain.tools.get(tool_name)

    assert tool is not None
    schema = tool.schema()["input_schema"]
    assert schema.get("type") == "object"
    assert isinstance(schema.get("properties"), dict)
    for field in required_fields:
        assert field in schema.get("required", [])

    result = tool.handler(**payload)

    assert isinstance(result, dict)
    assert result.get("status") == "pending_approval"
    assert isinstance(result.get("approval_id"), str)
    assert result.get("approval_id")
    assert result.get("kind") == tool_name