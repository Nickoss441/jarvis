"""Security fixture tests for policy-denied prompt injection and unsafe args."""

from pathlib import Path

import pytest

from jarvis.policy import Policy

from .security_fixtures import (
    ALL_SECURITY_CASES,
    PROMPT_INJECTION_CASES,
    UNSAFE_TOOL_ARGUMENT_CASES,
)


def _repo_policy() -> Policy:
    repo_root = Path(__file__).resolve().parents[1]
    return Policy.from_file(repo_root / "policies.yaml")


@pytest.mark.parametrize("case", ALL_SECURITY_CASES, ids=[c["id"] for c in ALL_SECURITY_CASES])
def test_security_cases_are_denied_by_policy(case) -> None:
    policy = _repo_policy()

    decision = policy.check_tool(case["tool"], case["args"])

    assert decision.allowed is False
    assert isinstance(decision.reason, str)
    assert decision.reason.strip()


def test_security_fixtures_cover_prompt_injection_and_unsafe_arguments() -> None:
    assert PROMPT_INJECTION_CASES
    assert UNSAFE_TOOL_ARGUMENT_CASES

    prompt_tools = {c["tool"] for c in PROMPT_INJECTION_CASES}
    unsafe_tools = {c["tool"] for c in UNSAFE_TOOL_ARGUMENT_CASES}

    assert "web_search" in prompt_tools or "web_fetch" in prompt_tools
    assert "notes_write" in unsafe_tools
    assert "shell_run" in unsafe_tools
