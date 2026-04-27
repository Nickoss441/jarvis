"""Tests for the Brain loop using a mocked Anthropic client."""
import types
from pathlib import Path
from typing import Any

import pytest

from jarvis.approval_service import ApprovalService
from jarvis.audit import AuditLog
from jarvis.brain import Brain
from jarvis.config import Config
from jarvis.event_bus import EventBus
from jarvis.policy import Policy
from jarvis.runtime import RuntimeEventEnvelope
from jarvis.tools import Tool, ToolRegistry
from jarvis.tools.eta_to import make_eta_to_tool
from jarvis.tools.location_current import make_location_current_tool
from jarvis.tools.message_send import make_message_send_tool
from jarvis.tools.weather_here import make_weather_here_tool


class _Block:
    def __init__(self, block_type: str, **kwargs: Any) -> None:
        self.type = block_type
        for k, v in kwargs.items():
            setattr(self, k, v)


class _Response:
    def __init__(self, stop_reason: str, content: list[Any]):
        self.stop_reason = stop_reason
        self.content = content


class _MessagesAPI:
    def __init__(self, responses: list[_Response]):
        self._responses = responses
        self.calls = 0

    def create(self, **_kwargs: Any) -> _Response:
        idx = min(self.calls, len(self._responses) - 1)
        self.calls += 1
        return self._responses[idx]


def _build_brain(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    responses: list[_Response],
    policy: Policy | None = None,
) -> tuple[Brain, Any]:
    fake_client = types.SimpleNamespace(messages=_MessagesAPI(responses))

    def _make_client(api_key: str) -> Any:
        return fake_client

    monkeypatch.setitem(
        __import__("sys").modules,
        "anthropic",
        types.SimpleNamespace(Anthropic=_make_client),
    )

    config = Config(
        anthropic_api_key="test-key",
        model="claude-sonnet-4-6",
        notes_dir=tmp_path / "notes",
        audit_db=tmp_path / "audit.db",
        conversation_store_path=tmp_path / "conversation.json",
        user_name="Nick",
    )
    audit = AuditLog(config.audit_db)
    tools = ToolRegistry()
    def _echo_handler(text: str) -> dict[str, Any]:
        return {"echo": text}

    tools.register(
        Tool(
            name="echo",
            description="Echo input",
            input_schema={
                "type": "object",
                "properties": {"text": {"type": "string"}},
                "required": ["text"],
            },
            handler=_echo_handler,
        )
    )
    return Brain(config, audit, policy or Policy(rules={}), tools), fake_client


def test_turn_returns_text_without_tools(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    responses = [_Response("end_turn", [_Block("text", text="hello")])]
    brain, _ = _build_brain(tmp_path, monkeypatch, responses)

    out = brain.turn("hi")

    assert out == "hello"
    rows = brain.audit.recent(limit=10)
    assert any(r["kind"] == "user_input" for r in rows)
    assert any(r["kind"] == "llm_response" for r in rows)


def test_default_system_prompt_is_structured(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    responses = [_Response("end_turn", [_Block("text", text="hello")])]
    brain, _ = _build_brain(tmp_path, monkeypatch, responses)

    prompt = brain._system()

    assert "<identity>" in prompt
    assert "<tool_families>" in prompt
    assert "<turn_structure>" in prompt
    assert "<planning_rules>" in prompt
    assert "<response_contract>" in prompt
    assert "Nick" in prompt
    assert "check calendar_read before making a plan" in prompt


def test_turn_executes_tools_then_returns_text(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    responses = [
        _Response(
            "tool_use",
            [
                _Block("text", text="Thought: Looking that up..."),
                _Block("tool_use", id="t1", name="echo", input={"text": "pong"}),
            ],
        ),
        _Response("end_turn", [_Block("text", text="done")]),
    ]
    brain, _ = _build_brain(tmp_path, monkeypatch, responses)

    out = brain.turn("ping")

    assert out == "done"
    # user + assistant(tool_use) + user(tool_result) + assistant(text)
    assert len(brain.conversation.messages) == 4
    assistant_tool_use_msg = brain.conversation.messages[1]
    assert assistant_tool_use_msg["content"][0] == {"type": "text", "text": "Thought: Looking that up..."}
    tool_result_msg = brain.conversation.messages[2]
    assert tool_result_msg["role"] == "user"
    assert tool_result_msg["content"][0]["type"] == "tool_result"
    assert tool_result_msg["content"][0]["content"].startswith("Observation: ")
    assert "pong" in tool_result_msg["content"][0]["content"]
    rows = brain.audit.recent(limit=20)
    assert any(r["kind"] == "tool_call" for r in rows)
    assert any(r["kind"] == "tool_result" for r in rows)
    assert len(brain._active_turn.react_cycles) == 2
    assert brain._active_turn.react_cycles[0]["thought"] == "Looking that up..."
    assert brain._active_turn.react_cycles[0]["actions"][0]["tool_name"] == "echo"
    assert brain._active_turn.react_cycles[0]["observations"][0]["result"] == {"echo": "pong"}
    assert brain._active_turn.react_cycles[0]["completed"] is True
    assert brain._active_turn.react_cycles[1]["final_text"] == "done"


def test_turn_normalizes_plain_text_into_thought_prefix_for_tool_cycle(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    responses = [
        _Response(
            "tool_use",
            [
                _Block("text", text="Looking that up..."),
                _Block("tool_use", id="t1", name="echo", input={"text": "pong"}),
            ],
        ),
        _Response("end_turn", [_Block("text", text="done")]),
    ]
    brain, _ = _build_brain(tmp_path, monkeypatch, responses)

    out = brain.turn("ping")

    assert out == "done"
    assistant_tool_use_msg = brain.conversation.messages[1]
    assert assistant_tool_use_msg["content"][0] == {"type": "text", "text": "Thought: Looking that up..."}
    assert brain._active_turn.react_cycles[0]["thought"] == "Looking that up..."


def test_turn_handles_non_object_tool_input_with_typed_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    responses = [
        _Response(
            "tool_use",
            [
                _Block("tool_use", id="bad-1", name="echo", input=["not", "object"]),
            ],
        ),
        _Response("end_turn", [_Block("text", text="done")]),
    ]
    brain, _ = _build_brain(tmp_path, monkeypatch, responses)

    out = brain.turn("ping")

    assert out == "done"
    tool_result_msg = brain.conversation.messages[2]
    assert tool_result_msg["role"] == "user"
    payload = tool_result_msg["content"][0]["content"]
    assert "tool-bad-args" in payload
    assert "tool input must be an object" in payload

    rows = brain.audit.recent(limit=20)
    tool_call_rows = [row for row in rows if row["kind"] == "tool_call"]
    assert tool_call_rows
    assert tool_call_rows[0]["payload"]["policy"]["reason"] == "invalid_tool_input"


def test_turn_handles_block_missing_type_without_crashing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    malformed_block = types.SimpleNamespace(name="echo", input={"text": "pong"})
    responses = [
        _Response("tool_use", [malformed_block]),
        _Response("end_turn", [_Block("text", text="done")]),
    ]
    brain, _ = _build_brain(tmp_path, monkeypatch, responses)

    out = brain.turn("ping")

    assert out == "done"
    assistant_msg = brain.conversation.messages[1]
    assert assistant_msg["role"] == "assistant"
    assert assistant_msg["content"][0]["type"] == "unknown"

    rows = brain.audit.recent(limit=20)
    tool_calls = [row for row in rows if row["kind"] == "tool_call"]
    assert tool_calls == []


def test_turn_audit_events_share_same_correlation_id(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    responses = [
        _Response(
            "tool_use",
            [_Block("tool_use", id="t-corr", name="echo", input={"text": "pong"})],
        ),
        _Response("end_turn", [_Block("text", text="done")]),
    ]
    brain, _ = _build_brain(tmp_path, monkeypatch, responses)

    out = brain.turn("ping")

    assert out == "done"

    rows = brain.audit.recent(limit=20)
    by_kind = {row["kind"]: row["payload"] for row in rows}

    corr = by_kind["user_input"]["correlation_id"]
    assert corr
    assert by_kind["llm_response"]["correlation_id"] == corr
    assert by_kind["tool_call"]["correlation_id"] == corr
    assert by_kind["tool_result"]["correlation_id"] == corr
    assert by_kind["tool_call"]["tool_use_id"] == "t-corr"
    assert by_kind["tool_result"]["tool_use_id"] == "t-corr"


def test_brain_restores_persisted_conversation_on_restart(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    responses = [_Response("end_turn", [_Block("text", text="hello")])]
    brain, _ = _build_brain(tmp_path, monkeypatch, responses)

    assert brain.turn("hi") == "hello"

    restored_brain, _ = _build_brain(tmp_path, monkeypatch, responses)

    assert restored_brain.conversation.messages[0] == {"role": "user", "content": "hi"}
    assert restored_brain.conversation.messages[1]["role"] == "assistant"


def test_run_tool_denied_by_policy(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    responses = [_Response("end_turn", [_Block("text", text="ok")])]
    policy = Policy(rules={"blocked_tools": ["echo"]})
    brain, _ = _build_brain(tmp_path, monkeypatch, responses, policy=policy)

    result = brain.run_tool("echo", {"text": "x"})

    assert result["error"] == "policy-denied"
    assert result["tool_name"] == "echo"


def test_run_tool_checks_policy_once_at_dispatch_boundary(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    responses = [_Response("end_turn", [_Block("text", text="ok")])]
    brain, _ = _build_brain(tmp_path, monkeypatch, responses)

    calls: list[Any] = []

    def _fake_preflight(name: str, args: dict[str, Any]) -> Any:
        calls.append((name, args))
        return Policy(rules={"blocked_tools": ["echo"]}).check_tool(name, args)

    monkeypatch.setattr(brain, "_preflight", _fake_preflight)

    result = brain.run_tool("echo", {"text": "x"})

    assert calls == [("echo", {"text": "x"})]
    assert result["error"] == "policy-denied"


def test_dispatch_returns_typed_error_for_unknown_tool(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    responses = [_Response("end_turn", [_Block("text", text="ok")])]
    brain, _ = _build_brain(tmp_path, monkeypatch, responses)

    result = brain.run_tool("no_such_tool", {})

    assert result["error"] == "tool-not-found"
    assert result["tool_name"] == "no_such_tool"


def test_dispatch_returns_typed_error_for_bad_args(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    responses = [_Response("end_turn", [_Block("text", text="ok")])]
    brain, _ = _build_brain(tmp_path, monkeypatch, responses)

    result = brain.run_tool("echo", {"wrong_arg": "x"})

    assert result["error"] == "tool-bad-args"
    assert result["tool_name"] == "echo"
    assert "detail" in result


def test_dispatch_returns_typed_error_for_handler_exception(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from jarvis.tools import Tool

    responses = [_Response("end_turn", [_Block("text", text="ok")])]
    brain, _ = _build_brain(tmp_path, monkeypatch, responses)
    brain.tools.register(
        Tool(
            name="boom",
            description="Always raises",
            input_schema={"type": "object", "properties": {}},
            handler=lambda: (_ for _ in ()).throw(RuntimeError("kaboom")),
        )
    )

    result = brain.run_tool("boom", {})

    assert result["error"] == "tool-failure"


def test_dispatch_retries_transient_failure_and_succeeds(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Tool raises once then succeeds — dispatch must return the success result."""
    from jarvis.runtime.retry import RetryPolicy
    from jarvis.tools import Tool

    responses = [_Response("end_turn", [_Block("text", text="ok")])]
    brain, _ = _build_brain(tmp_path, monkeypatch, responses)
    brain.retry_policy = RetryPolicy(max_attempts=2)

    call_count = [0]

    def _flaky():
        call_count[0] += 1
        if call_count[0] == 1:
            raise RuntimeError("transient glitch")
        return {"ok": True}

    brain.tools.register(
        Tool(
            name="flaky",
            description="Fails once then succeeds",
            input_schema={"type": "object", "properties": {}},
            handler=_flaky,
        )
    )

    result = brain.run_tool("flaky", {})

    assert result == {"ok": True}
    assert call_count[0] == 2


def test_dispatch_exhausts_retries_and_returns_tool_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Tool always raises — dispatch must return tool-failure after all attempts."""
    from jarvis.runtime.retry import RetryPolicy
    from jarvis.tools import Tool

    responses = [_Response("end_turn", [_Block("text", text="ok")])]
    brain, _ = _build_brain(tmp_path, monkeypatch, responses)
    brain.retry_policy = RetryPolicy(max_attempts=3)

    call_count = [0]

    def _always_fails():
        call_count[0] += 1
        raise RuntimeError("always broken")

    brain.tools.register(
        Tool(
            name="broken",
            description="Always raises",
            input_schema={"type": "object", "properties": {}},
            handler=_always_fails,
        )
    )

    result = brain.run_tool("broken", {})

    assert result["error"] == "tool-failure"


def test_end_to_end_request_approval_tool_action_and_audit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    responses = [
        _Response(
            "tool_use",
            [
                _Block(
                    "tool_use",
                    id="t-msg-1",
                    name="message_send",
                    input={
                        "channel": "email",
                        "recipient": "user@example.com",
                        "subject": "Hi",
                        "body": "hello",
                    },
                )
            ],
        ),
        _Response("end_turn", [_Block("text", text="approval queued")]),
    ]
    fake_client = types.SimpleNamespace(messages=_MessagesAPI(responses))

    def _make_client(api_key: str) -> Any:
        return fake_client

    monkeypatch.setitem(
        __import__("sys").modules,
        "anthropic",
        types.SimpleNamespace(Anthropic=_make_client),
    )

    config = Config(
        anthropic_api_key="test-key",
        model="claude-sonnet-4-6",
        notes_dir=tmp_path / "notes",
        audit_db=tmp_path / "audit.db",
        approval_db=tmp_path / "approvals.db",
        message_outbox=tmp_path / "outbox.jsonl",
        user_name="Nick",
    )
    audit = AuditLog(config.audit_db)
    policy = Policy(rules={})
    approval_service = ApprovalService(config)
    tools = ToolRegistry()
    tools.register(
        make_message_send_tool(
            request_approval=approval_service.request,
            get_approval=approval_service.store.get,
        )
    )
    brain = Brain(config, audit, policy, tools)

    out = brain.turn("Send a quick hello email")

    assert out == "approval queued"
    pending = approval_service.list_pending(limit=10)
    assert len(pending) == 1

    approval_id = pending[0]["id"]
    assert approval_service.approve(approval_id, reason="looks good")

    summary = approval_service.dispatch(limit=10)

    assert summary.failures == 0
    assert len(summary.items) == 1

    processed = approval_service.store.get(approval_id)
    assert processed is not None
    assert processed["status"] == "processed"
    assert processed["dispatch_result"]["status"] == "dry_run_sent"

    rows = audit.recent(limit=20)
    kinds = [row["kind"] for row in rows]
    assert "user_input" in kinds
    assert "tool_call" in kinds
    assert "tool_result" in kinds
    assert "approval_requested" in kinds
    assert "approval_approved" in kinds
    assert "approval_dispatched" in kinds


def test_turn_stops_after_max_iterations(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from jarvis import brain as brain_module

    monkeypatch.setattr(brain_module, "MAX_ITERATIONS", 2)
    responses = [
        _Response(
            "tool_use",
            [_Block("tool_use", id="t1", name="echo", input={"text": "x"})],
        )
    ]
    brain, _ = _build_brain(tmp_path, monkeypatch, responses)

    out = brain.turn("loop")

    assert out == "(stopped after max iterations — task too long for one turn)"


def test_turn_executes_location_wrapper_tools_with_seeded_location(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    responses = [
        _Response(
            "tool_use",
            [
                _Block(
                    "tool_use",
                    id="t-weather",
                    name="weather_here",
                    input={"units": "metric", "max_age_seconds": 600},
                ),
                _Block(
                    "tool_use",
                    id="t-eta",
                    name="eta_to",
                    input={
                        "destination_latitude": 52.5200,
                        "destination_longitude": 13.4050,
                        "transport": "driving",
                        "max_age_seconds": 600,
                    },
                ),
            ],
        ),
        _Response("end_turn", [_Block("text", text="ready")]),
    ]
    fake_client = types.SimpleNamespace(messages=_MessagesAPI(responses))

    def _make_client(api_key: str) -> Any:
        return fake_client

    monkeypatch.setitem(
        __import__("sys").modules,
        "anthropic",
        types.SimpleNamespace(Anthropic=_make_client),
    )

    config = Config(
        anthropic_api_key="test-key",
        model="claude-sonnet-4-6",
        notes_dir=tmp_path / "notes",
        audit_db=tmp_path / "audit.db",
        event_bus_db=tmp_path / "event-bus.db",
        user_name="Nick",
    )
    audit = AuditLog(config.audit_db)
    policy = Policy(rules={})
    tools = ToolRegistry()
    bus = EventBus(config.event_bus_db)
    bus.emit(
        RuntimeEventEnvelope(
            kind="location_update",
            source="ios-shortcut",
            payload={"latitude": 52.3676, "longitude": 4.9041, "accuracy_m": 7.0},
        )
    )
    tools.register(make_location_current_tool(bus))
    tools.register(make_weather_here_tool(bus, mode="dry_run"))
    tools.register(make_eta_to_tool(bus, mode="dry_run"))
    brain = Brain(config, audit, policy, tools)

    out = brain.turn("How's weather here and ETA to Berlin?")

    assert out == "ready"
    tool_result_msg = brain.conversation.messages[2]
    assert tool_result_msg["role"] == "user"
    assert len(tool_result_msg["content"]) == 2
    assert tool_result_msg["content"][0]["type"] == "tool_result"
    assert "temperature_c" in tool_result_msg["content"][0]["content"]
    assert tool_result_msg["content"][1]["type"] == "tool_result"
    assert "eta_minutes" in tool_result_msg["content"][1]["content"]

    rows = audit.recent(limit=20)
    tool_call_names = [
        row["payload"]["name"]
        for row in rows
        if row["kind"] == "tool_call"
    ]
    assert "weather_here" in tool_call_names
    assert "eta_to" in tool_call_names


def test_turn_uses_explicit_runtime_stages_in_order(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    responses = [
        _Response(
            "tool_use",
            [_Block("tool_use", id="t1", name="echo", input={"text": "pong"})],
        ),
        _Response("end_turn", [_Block("text", text="done")]),
    ]
    brain, _ = _build_brain(tmp_path, monkeypatch, responses)

    calls: list[Any] = []

    real_perceive: Any = getattr(brain, "_perceive")
    real_plan: Any = getattr(brain, "_plan")
    real_observe: Any = getattr(brain, "_observe")
    real_preflight: Any = getattr(brain, "_preflight")
    real_dispatch_requested_tools: Any = getattr(brain, "_dispatch_requested_tools")

    def _wrap_perceive(turn: Any) -> None:
        calls.append("perceive")
        return real_perceive(turn)

    def _wrap_plan(turn: Any) -> Any:
        calls.append("plan")
        return real_plan(turn)

    def _wrap_observe(response: Any, correlation_id: str) -> Any:
        calls.append("observe")
        return real_observe(response, correlation_id)

    def _wrap_preflight(name: str, args: dict[str, Any]) -> Any:
        calls.append(f"preflight:{name}")
        return real_preflight(name, args)

    def _wrap_dispatch_requested_tools(response: Any, turn: Any) -> Any:
        calls.append("dispatch")
        return real_dispatch_requested_tools(response, turn)

    monkeypatch.setattr(brain, "_perceive", _wrap_perceive)
    monkeypatch.setattr(brain, "_plan", _wrap_plan)
    monkeypatch.setattr(brain, "_observe", _wrap_observe)
    monkeypatch.setattr(brain, "_preflight", _wrap_preflight)
    monkeypatch.setattr(brain, "_dispatch_requested_tools", _wrap_dispatch_requested_tools)

    out = brain.turn("ping")

    assert out == "done"
    assert calls == [
        "perceive",
        "plan",
        "observe",
        "dispatch",
        "preflight:echo",
        "plan",
        "observe",
    ]

    