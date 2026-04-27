from jarvis.runtime import RetryPolicy, RuntimeEventEnvelope, RuntimeOrchestrator, RuntimeToolError, RuntimeTurnContext


class _Block:
    def __init__(self, block_type: str, text: str = ""):
        self.type = block_type
        self.text = text


def test_runtime_orchestrator_starts_turn_context():
    orchestrator = RuntimeOrchestrator(max_iterations=3)

    turn = orchestrator.start_turn("hello", "corr-123")

    assert isinstance(turn, RuntimeTurnContext)
    assert turn.user_input == "hello"
    assert turn.correlation_id == "corr-123"
    assert turn.max_iterations == 3
    assert turn.iteration == 0
    assert not turn.exhausted


def test_runtime_turn_context_tracks_iterations_and_tool_results():
    turn = RuntimeTurnContext(user_input="hello", correlation_id="corr", max_iterations=2)

    assert turn.advance_iteration() == 1
    block = turn.add_tool_result("tool-1", {"ok": True})
    assert block == {
        "type": "tool_result",
        "tool_use_id": "tool-1",
        "content": "Observation: {'ok': True}",
    }
    assert not turn.exhausted

    assert turn.advance_iteration() == 2
    assert turn.exhausted


def test_runtime_turn_context_tracks_react_cycle_state():
    turn = RuntimeTurnContext(user_input="hello", correlation_id="corr", max_iterations=2)

    turn.advance_iteration()
    turn.begin_react_cycle()
    turn.record_thought("Need to inspect state")
    turn.record_action("desktop_control", {"action": "active_window"}, tool_use_id="tool-1")
    turn.record_observation("desktop_control", {"ok": True, "app": "Safari"}, tool_use_id="tool-1")
    cycle = turn.complete_react_cycle(final_text="done")

    assert cycle == {
        "iteration": 1,
        "thought": "Need to inspect state",
        "actions": [
            {
                "tool_name": "desktop_control",
                "tool_use_id": "tool-1",
                "args": {"action": "active_window"},
            }
        ],
        "observations": [
            {
                "tool_name": "desktop_control",
                "tool_use_id": "tool-1",
                "result": {"ok": True, "app": "Safari"},
            }
        ],
        "final_text": "done",
        "completed": True,
    }


def test_runtime_orchestrator_collects_final_text_blocks():
    blocks = [_Block("text", "hello "), _Block("text", "world"), _Block("tool_use")]

    result = RuntimeOrchestrator.final_text_from_blocks(blocks)

    assert result == "hello world"


def test_runtime_orchestrator_collects_plain_text_without_default_fallback():
    blocks = [_Block("text", "think "), _Block("text", "first")]

    result = RuntimeOrchestrator.text_from_blocks(blocks)

    assert result == "think first"


def test_runtime_orchestrator_returns_default_for_missing_text():
    result = RuntimeOrchestrator.final_text_from_blocks([_Block("tool_use")])

    assert result == "(no text response)"


def test_runtime_event_envelope_defaults_correlation_id_to_event_id():
    event = RuntimeEventEnvelope(kind="webhook", source="webhook_demo", payload={"ok": True})

    assert event.correlation_id == event.id


def test_runtime_event_envelope_promotes_payload_correlation_id():
    event = RuntimeEventEnvelope(
        kind="webhook",
        source="webhook_demo",
        payload={"correlation_id": "corr-from-payload", "ok": True},
    )

    assert event.correlation_id == "corr-from-payload"
    restored = RuntimeEventEnvelope.from_dict(event.to_dict())
    assert restored.correlation_id == "corr-from-payload"


def test_runtime_tool_error_carries_kind_and_name():
    err = RuntimeToolError(
        kind="policy-denied",
        tool_name="payments",
        message="policy preflight denied this tool call",
        detail="tool 'payments' requires phase 'payments'",
    )

    assert err.kind == "policy-denied"
    assert err.tool_name == "payments"
    d = err.to_dict()
    assert d["error"] == "policy-denied"
    assert d["tool_name"] == "payments"
    assert d["message"] == "policy preflight denied this tool call"
    assert "requires phase" in d["detail"]


def test_runtime_tool_error_all_kinds_are_accepted():
    for kind in ("policy-denied", "tool-not-found", "tool-failure", "tool-bad-args"):
        err = RuntimeToolError(kind=kind, tool_name="demo", message="test")  # type: ignore[arg-type]
        assert err.to_dict()["error"] == kind


# ---------------------------------------------------------------------------
# RetryPolicy
# ---------------------------------------------------------------------------

def test_retry_policy_default_max_attempts_is_two():
    policy = RetryPolicy()
    assert policy.max_attempts == 2


def test_retry_policy_should_retry_before_last_attempt():
    policy = RetryPolicy(max_attempts=3)
    # attempts 1 and 2 should retry; attempt 3 should not
    assert policy.should_retry(1) is True
    assert policy.should_retry(2) is True
    assert policy.should_retry(3) is False


def test_retry_policy_max_attempts_one_never_retries():
    policy = RetryPolicy(max_attempts=1)
    assert policy.should_retry(1) is False


def test_retry_policy_rejects_zero_max_attempts():
    import pytest
    with pytest.raises(ValueError, match="max_attempts"):
        RetryPolicy(max_attempts=0)
