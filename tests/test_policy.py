"""Tests for the policy engine. No API keys required."""
import datetime
from pathlib import Path

import pytest

from jarvis.policy import (
    Policy,
    PolicyRateLimiter,
    QuietHoursRule,
    RateLimitRule,
    ScheduleRule,
)


def test_empty_policy_allows_everything():
    p = Policy(rules={})
    assert p.check_tool("anything", {}).allowed
    assert p.check_tool("web_fetch", {"url": "https://example.com"}).allowed


def test_blocked_tool_denied():
    p = Policy(rules={"blocked_tools": ["notes_write"]})
    decision = p.check_tool("notes_write", {"path": "x.md", "content": "y"})
    assert not decision.allowed
    assert "blocked_tools" in decision.reason


@pytest.mark.parametrize(
    ("tool_name", "payload"),
    [
        ("message_send", {"channel": "sms", "recipient": "+14155552671", "body": "hello"}),
        ("call_phone", {"phone_number": "+14155552671", "message": "hello"}),
        ("payments", {"merchant": "Coffee Shop", "amount": 4.5, "currency": "USD"}),
        ("trade", {"instrument": "AAPL", "side": "buy", "size": 1, "rationale": "test"}),
        ("shell_run", {"command": "echo hello"}),
        ("file_write", {"path": "scratch/out.txt", "content": "hello"}),
        ("install_app", {"app": "spotify"}),
    ],
)
def test_policy_blocked_tools_can_preflight_deny_every_gated_tool(tool_name, payload):
    decision = Policy(rules={"blocked_tools": [tool_name]}).check_tool(tool_name, payload)

    assert not decision.allowed
    assert "blocked_tools" in decision.reason


def test_blocked_domain_in_url():
    p = Policy(rules={"blocked_domains": ["evil.example"]})
    assert not p.check_tool(
        "web_fetch", {"url": "https://evil.example/page"}
    ).allowed
    assert p.check_tool(
        "web_fetch", {"url": "https://safe.example/page"}
    ).allowed


def test_blocked_domain_in_query():
    p = Policy(rules={"blocked_domains": ["evil.example"]})
    assert not p.check_tool(
        "web_search", {"query": "site:evil.example login"}
    ).allowed


def test_allowed_domains_allows_matching_url_target():
    p = Policy(rules={"allowed_domains": ["example.com"]})

    decision = p.check_tool("web_fetch", {"url": "https://docs.example.com/page"})

    assert decision.allowed


def test_allowed_domains_denies_non_matching_url_target():
    p = Policy(rules={"allowed_domains": ["example.com"]})

    decision = p.check_tool("web_fetch", {"url": "https://evil.test/page"})

    assert not decision.allowed
    assert "allowlist" in decision.reason


def test_domain_allowlist_alias_is_honored():
    p = Policy(rules={"domain_allowlist": ["safe.example"]})

    decision = p.check_tool("web_fetch", {"url": "https://safe.example/page"})

    assert decision.allowed


def test_domain_blocks_alias_is_honored():
    p = Policy(rules={"domain_blocks": ["forbidden.example"]})

    decision = p.check_tool("web_fetch", {"url": "https://forbidden.example/page"})

    assert not decision.allowed
    assert "blocked domain" in decision.reason


def test_notes_write_path_traversal_denied():
    p = Policy(rules={})
    assert not p.check_tool(
        "notes_write", {"path": "../etc/passwd", "content": "x"}
    ).allowed
    assert not p.check_tool(
        "notes_write", {"path": "/etc/passwd", "content": "x"}
    ).allowed
    assert not p.check_tool(
        "notes_write", {"path": "", "content": "x"}
    ).allowed


def test_notes_write_relative_path_allowed():
    p = Policy(rules={})
    assert p.check_tool(
        "notes_write", {"path": "inbox/today.md", "content": "x"}
    ).allowed


def test_global_path_guard_blocks_path_traversal_for_any_tool():
    p = Policy(rules={})

    decision = p.check_tool("file_write", {"path": "../escape.txt", "content": "x"})

    assert not decision.allowed
    assert "unsafe path" in decision.reason


def test_global_path_guard_blocks_absolute_path_for_any_tool():
    p = Policy(rules={})

    decision = p.check_tool("file_write", {"path": "/tmp/escape.txt", "content": "x"})

    assert not decision.allowed


def test_global_path_guard_can_be_disabled_with_notes_path_block_false():
    p = Policy(rules={"notes_path_block": False})

    decision = p.check_tool("file_write", {"path": "../escape.txt", "content": "x"})

    assert decision.allowed


def test_notes_read_path_traversal_denied_by_global_guard():
    p = Policy(rules={})

    decision = p.check_tool("notes_read", {"path": "../etc/passwd"})

    assert not decision.allowed
    assert "unsafe path" in decision.reason


def test_phase_required_tool_denied_when_phase_disabled():
    p = Policy(
        rules={"tool_phase_requirements": {"payments": "payments"}},
        enabled_phases=set(),
    )

    decision = p.check_tool("payments", {"amount": 10})

    assert not decision.allowed
    assert "requires phase 'payments'" in decision.reason


def test_phase_required_tool_allowed_when_phase_enabled():
    p = Policy(
        rules={"tool_phase_requirements": {"payments": "payments"}},
        enabled_phases={"payments"},
    )

    decision = p.check_tool("payments", {"amount": 10})

    assert decision.allowed


def test_multiple_concrete_phase_mappings_enforced():
    p = Policy(
        rules={
            "tool_phase_requirements": {
                "payments": "payments",
                "trade": "trading",
                "call_phone": "telephony",
                "message_send": "approvals",
                "install_app": "sandbox",
            }
        },
        enabled_phases={"approvals", "telephony", "sandbox"},
    )

    assert not p.check_tool("payments", {}).allowed
    assert not p.check_tool("trade", {}).allowed
    assert p.check_tool("call_phone", {}).allowed
    assert p.check_tool("message_send", {}).allowed
    assert p.check_tool("install_app", {}).allowed


def test_home_assistant_write_to_critical_entity_denied():
    p = Policy(
        rules={
            "critical_smart_home_entities": [
                "lock.*",
                "alarm_control_panel.*",
                "cover.garage*",
                "switch.oven*",
            ],
            "smart_home_write_actions": ["turn_off", "unlock", "arm"],
        }
    )

    decision = p.check_tool(
        "home_assistant",
        {"action": "turn_off", "entity_id": "switch.oven_main"},
    )

    assert not decision.allowed
    assert "critical smart-home entity" in decision.reason


def test_home_assistant_write_to_non_critical_entity_allowed():
    p = Policy(
        rules={
            "critical_smart_home_entities": ["lock.*", "alarm_control_panel.*"],
            "smart_home_write_actions": ["turn_on", "turn_off"],
        }
    )

    decision = p.check_tool(
        "home_assistant",
        {"action": "turn_on", "entity_id": "light.kitchen"},
    )

    assert decision.allowed


def test_home_assistant_read_for_critical_entity_allowed():
    p = Policy(rules={"critical_smart_home_entities": ["lock.*"]})

    decision = p.check_tool(
        "home_assistant",
        {"action": "get_state", "entity_id": "lock.front_door"},
    )

    assert decision.allowed


def test_home_assistant_service_data_entity_list_denied_for_critical_entities():
    p = Policy(
        rules={
            "critical_smart_home_entities": ["lock.*", "cover.garage*"],
            "smart_home_write_actions": ["call_service"],
        }
    )

    decision = p.check_tool(
        "home_assistant",
        {
            "action": "call_service",
            "service": "lock.unlock",
            "service_data": {
                "entity_ids": ["lock.front_door", "light.kitchen"],
            },
        },
    )

    assert not decision.allowed
    assert "lock.front_door" in decision.reason


# ---------------------------------------------------------------------------
# QuietHoursRule unit tests
# ---------------------------------------------------------------------------

def _dt(hour: int) -> datetime.datetime:
    """Return a fixed datetime with the given hour for deterministic tests."""
    return datetime.datetime(2026, 4, 26, hour, 0, 0)


def test_quiet_hours_rule_blocks_tool_during_quiet_window() -> None:
    rule = QuietHoursRule(start_hour=8, end_hour=22, blocked_tools=("call_phone",))
    # 23:00 is outside [8, 22)
    assert rule.denies("call_phone", _dt(23)) is True


def test_quiet_hours_rule_allows_tool_inside_allowed_window() -> None:
    rule = QuietHoursRule(start_hour=8, end_hour=22, blocked_tools=("call_phone",))
    # 10:00 is inside [8, 22)
    assert rule.denies("call_phone", _dt(10)) is False


def test_quiet_hours_rule_allows_unmatched_tool_during_quiet_window() -> None:
    rule = QuietHoursRule(start_hour=8, end_hour=22, blocked_tools=("call_phone",))
    # web_search is not in blocked_tools — should never be denied
    assert rule.denies("web_search", _dt(23)) is False


def test_quiet_hours_rule_boundary_exact_start_hour_is_allowed() -> None:
    rule = QuietHoursRule(start_hour=8, end_hour=22, blocked_tools=("call_phone",))
    # start_hour itself is inside the allowed window (inclusive)
    assert rule.denies("call_phone", _dt(8)) is False


def test_quiet_hours_rule_boundary_exact_end_hour_is_blocked() -> None:
    rule = QuietHoursRule(start_hour=8, end_hour=22, blocked_tools=("call_phone",))
    # end_hour is exclusive — 22:00 should be outside the allowed window
    assert rule.denies("call_phone", _dt(22)) is True


def test_quiet_hours_rule_empty_blocked_tools_never_denies() -> None:
    rule = QuietHoursRule(start_hour=8, end_hour=22, blocked_tools=())
    assert rule.denies("call_phone", _dt(23)) is False


def test_policy_check_tool_blocked_during_quiet_hours() -> None:
    policy = Policy(
        rules={},
        quiet_hours_rules=[
            QuietHoursRule(start_hour=8, end_hour=22, blocked_tools=("call_phone",)),
        ],
    )
    decision = policy.check_tool("call_phone", {}, _now=_dt(23))
    assert not decision.allowed
    assert "quiet hours" in decision.reason


def test_policy_check_tool_allowed_outside_quiet_window() -> None:
    policy = Policy(
        rules={},
        quiet_hours_rules=[
            QuietHoursRule(start_hour=8, end_hour=22, blocked_tools=("call_phone",)),
        ],
    )
    decision = policy.check_tool("call_phone", {}, _now=_dt(10))
    assert decision.allowed


def test_policy_check_tool_denies_call_phone_outside_contact_allowlist() -> None:
    policy = Policy(
        rules={"call_contact_allowlist": ["+1415555*", "+44207*"]},
    )

    decision = policy.check_tool(
        "call_phone",
        {"phone_number": "+33123456789", "message": "Hello"},
    )

    assert not decision.allowed
    assert "call_contact_allowlist" in decision.reason


def test_policy_check_tool_allows_call_phone_inside_contact_allowlist() -> None:
    policy = Policy(
        rules={"call_contact_allowlist": ["+1415555*", "+44207*"]},
    )

    decision = policy.check_tool(
        "call_phone",
        {"phone_number": "+14155552671", "message": "Hello"},
    )

    assert decision.allowed


def test_policy_check_tool_denies_reservation_call_outside_contact_allowlist() -> None:
    policy = Policy(
        rules={"call_contact_allowlist": ["+1415555*", "+44207*"]},
    )

    decision = policy.check_tool(
        "reservation_call",
        {"phone_number": "+33123456789"},
    )

    assert not decision.allowed
    assert "call_contact_allowlist" in decision.reason


def test_schedule_rule_blocks_weekend_spend_tool() -> None:
    p = Policy(
        rules={},
        schedule_rules=[
            # Block payments/trade on Saturday (5) and Sunday (6)
            ScheduleRule(
                weekdays=(5, 6),
                blocked_tools=("payments", "trade"),
            ),
        ],
    )

    saturday = datetime.datetime(2026, 4, 25, 12, 0, 0)  # weekday=5
    decision = p.check_tool("payments", {"amount": 10}, _now=saturday)

    assert not decision.allowed
    assert "schedule rule" in decision.reason


def test_schedule_rule_allows_weekday_spend_tool() -> None:
    p = Policy(
        rules={},
        schedule_rules=[
            ScheduleRule(
                weekdays=(5, 6),
                blocked_tools=("payments",),
            ),
        ],
    )

    monday = datetime.datetime(2026, 4, 27, 12, 0, 0)  # weekday=0
    decision = p.check_tool("payments", {"amount": 10}, _now=monday)

    assert decision.allowed


def test_policy_from_file_loads_quiet_hours(tmp_path: "Path") -> None:
    from pathlib import Path

    yaml_text = """
quiet_hours:
  - start_hour: 8
    end_hour: 22
    blocked_tools:
      - call_phone
      - payments
"""
    p = tmp_path / "policies.yaml"
    p.write_text(yaml_text)

    policy = Policy.from_file(p)

    assert len(policy.quiet_hours_rules) == 1
    rule = policy.quiet_hours_rules[0]
    assert rule.start_hour == 8
    assert rule.end_hour == 22
    assert "call_phone" in rule.blocked_tools
    assert "payments" in rule.blocked_tools


def test_policy_from_file_loads_schedule_rules(tmp_path: "Path") -> None:
    yaml_text = """
schedule_rules:
  - weekdays: [5, 6]
    blocked_tools:
      - payments
      - trade
"""
    p = tmp_path / "policies.yaml"
    p.write_text(yaml_text)

    policy = Policy.from_file(p)

    assert len(policy.schedule_rules) == 1
    rule = policy.schedule_rules[0]
    assert rule.weekdays == (5, 6)
    assert "payments" in rule.blocked_tools


def test_policy_from_file_loads_call_contact_allowlist(tmp_path: "Path") -> None:
        yaml_text = """
call_contact_allowlist:
    - +1415555*
    - +44207*
"""
        p = tmp_path / "policies.yaml"
        p.write_text(yaml_text)

        policy = Policy.from_file(p)

        assert policy.rules["call_contact_allowlist"] == ["+1415555*", "+44207*"]


# ---------------------------------------------------------------------------
# RateLimitRule / PolicyRateLimiter
# ---------------------------------------------------------------------------


def test_rate_limiter_allows_calls_within_limit() -> None:
    rl = PolicyRateLimiter([RateLimitRule(tool_pattern="pay", max_calls=3, window_seconds=60)])
    t = 0.0
    assert rl.check("pay", _now=t)[0] is True
    t += 1
    assert rl.check("pay", _now=t)[0] is True
    t += 1
    assert rl.check("pay", _now=t)[0] is True


def test_rate_limiter_denies_at_limit() -> None:
    rl = PolicyRateLimiter([RateLimitRule(tool_pattern="pay", max_calls=2, window_seconds=60)])
    rl.check("pay", _now=0.0)
    rl.check("pay", _now=1.0)
    allowed, reason = rl.check("pay", _now=2.0)
    assert allowed is False
    assert "exceeded rate limit" in reason


def test_rate_limiter_window_expiry_resets_counter() -> None:
    rl = PolicyRateLimiter([RateLimitRule(tool_pattern="pay", max_calls=2, window_seconds=10)])
    rl.check("pay", _now=0.0)
    rl.check("pay", _now=1.0)
    allowed, _ = rl.check("pay", _now=20.0)
    assert allowed is True


def test_rate_limiter_ignores_unrelated_tools() -> None:
    rl = PolicyRateLimiter([RateLimitRule(tool_pattern="pay", max_calls=1, window_seconds=60)])
    for _ in range(10):
        allowed, _ = rl.check("web_search", _now=0.0)
        assert allowed is True


def test_policy_check_tool_rate_limited_returns_denial() -> None:
    rule = RateLimitRule(tool_pattern="trade", max_calls=1, window_seconds=60)
    limiter = PolicyRateLimiter([rule])
    p = Policy(rules={}, rate_limiter=limiter)
    decision1 = p.check_tool("trade", {})
    assert decision1.allowed is True
    decision2 = p.check_tool("trade", {})
    assert decision2.allowed is False
    assert "exceeded rate limit" in decision2.reason


def test_shell_run_sandbox_profile_blocks_command_prefix() -> None:
    p = Policy(
        rules={
            "sandbox_profiles": {
                "shell_run": {
                    "max_command_chars": 240,
                    "blocked_prefixes": ["rm", "sudo"],
                    "blocked_tokens": [],
                }
            }
        }
    )

    decision = p.check_tool("shell_run", {"command": "rm -rf ."})

    assert not decision.allowed
    assert "sandbox profile" in decision.reason


def test_shell_run_sandbox_profile_blocks_command_token() -> None:
    p = Policy(
        rules={
            "sandbox_profiles": {
                "shell_run": {
                    "max_command_chars": 240,
                    "blocked_prefixes": [],
                    "blocked_tokens": ["--no-preserve-root"],
                }
            }
        }
    )

    decision = p.check_tool("shell_run", {"command": "echo x --no-preserve-root"})

    assert not decision.allowed
    assert "sandbox profile" in decision.reason


def test_web_fetch_sandbox_profile_blocks_localhost_targets() -> None:
    p = Policy(
        rules={
            "sandbox_profiles": {
                "web_fetch": {
                    "max_chars_cap": 12000,
                    "blocked_hosts": ["localhost", "127.0.0.1"],
                }
            }
        }
    )

    decision = p.check_tool("web_fetch", {"url": "http://localhost:8000/health"})

    assert not decision.allowed
    assert "sandbox profile" in decision.reason


def test_web_fetch_sandbox_profile_caps_max_chars() -> None:
    p = Policy(
        rules={
            "sandbox_profiles": {
                "web_fetch": {
                    "max_chars_cap": 1000,
                    "blocked_hosts": [],
                }
            }
        }
    )

    decision = p.check_tool("web_fetch", {"url": "https://example.com", "max_chars": 5000})

    assert not decision.allowed
    assert "max_chars" in decision.reason


def test_policy_from_file_parses_rate_limits(tmp_path) -> None:
    pol_file = tmp_path / "policies.yaml"
    pol_file.write_text(
        "rate_limits:\n"
        "  - tool_pattern: call_phone\n"
        "    max_calls: 2\n"
        "    window_seconds: 30\n"
    )
    p = Policy.from_file(pol_file)
    rules = p.rate_limiter._rules
    assert len(rules) == 1
    assert rules[0].tool_pattern == "call_phone"
    assert rules[0].max_calls == 2
    assert rules[0].window_seconds == 30


def test_repo_policy_file_defines_rate_limits_for_payments_and_message_send() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    policy_path = repo_root / "policies.yaml"

    p = Policy.from_file(policy_path)

    rule_map = {
        r.tool_pattern: (r.max_calls, r.window_seconds)
        for r in p.rate_limiter._rules
    }
    assert rule_map.get("payments") == (3, 3600)
    assert rule_map.get("message_send") == (30, 3600)


def test_repo_policy_file_defines_call_phone_quiet_hours_and_allowlist() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    policy_path = repo_root / "policies.yaml"

    p = Policy.from_file(policy_path)

    assert any(
        rule.start_hour == 8
        and rule.end_hour == 21
        and "call_phone" in rule.blocked_tools
        for rule in p.quiet_hours_rules
    )
    assert p.rules.get("call_contact_allowlist") == ["+1415555*", "+44207*"]


def test_repo_policy_file_defines_sandbox_profiles_for_shell_and_web_fetch() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    policy_path = repo_root / "policies.yaml"

    p = Policy.from_file(policy_path)

    sandbox_profiles = p.rules.get("sandbox_profiles") or {}
    assert "shell_run" in sandbox_profiles
    assert "web_fetch" in sandbox_profiles
    assert sandbox_profiles["shell_run"]["max_command_chars"] == 240
    assert sandbox_profiles["web_fetch"]["max_chars_cap"] == 12000


def test_policy_schema_validation_valid_file_passes(tmp_path) -> None:
    pol_file = tmp_path / "policies.yaml"
    pol_file.write_text(
        "blocked_tools: []\n"
        "blocked_domains: []\n"
        "allowed_domains: []\n"
        "call_contact_allowlist: []\n"
        "quiet_hours: []\n"
        "rate_limits: []\n"
    )

    p = Policy.from_file(pol_file)

    assert p.rules["blocked_tools"] == []
    assert p.rules["blocked_domains"] == []
    assert p.rules["allowed_domains"] == []
    assert p.rules["call_contact_allowlist"] == []


def test_policy_schema_validation_unknown_key_raises(tmp_path) -> None:
    pol_file = tmp_path / "policies.yaml"
    pol_file.write_text(
        "blocked_tools: []\n"
        "unexpected_key: true\n"
    )

    import pytest

    with pytest.raises(ValueError, match="unknown policy keys"):
        Policy.from_file(pol_file)


def test_policy_schema_validation_wrong_type_raises(tmp_path) -> None:
    pol_file = tmp_path / "policies.yaml"
    pol_file.write_text(
        "blocked_tools: not-a-list\n"
    )

    import pytest

    with pytest.raises(ValueError, match="wrong type"):
        Policy.from_file(pol_file)


def test_policy_schema_validation_schedule_rules_invalid_weekday_raises(tmp_path) -> None:
    pol_file = tmp_path / "policies.yaml"
    pol_file.write_text(
        "schedule_rules:\n"
        "  - weekdays: [7]\n"
        "    blocked_tools: [payments]\n"
    )

    import pytest

    with pytest.raises(ValueError, match="range 0..6"):
        Policy.from_file(pol_file)


def test_policy_schema_validation_schedule_rules_missing_weekdays_raises(tmp_path) -> None:
    pol_file = tmp_path / "policies.yaml"
    pol_file.write_text(
        "schedule_rules:\n"
        "  - blocked_tools: [payments]\n"
    )

    import pytest

    with pytest.raises(ValueError, match="must not be empty"):
        Policy.from_file(pol_file)


def test_policy_schema_validation_quiet_hours_invalid_hour_raises(tmp_path) -> None:
    pol_file = tmp_path / "policies.yaml"
    pol_file.write_text(
        "quiet_hours:\n"
        "  - start_hour: 25\n"
        "    end_hour: 22\n"
        "    blocked_tools:\n"
        "      - call_phone\n"
    )

    import pytest

    with pytest.raises(ValueError, match="hours must be in range 0..23"):
        Policy.from_file(pol_file)


def test_policy_schema_validation_quiet_hours_blocked_tools_type_raises(tmp_path) -> None:
    pol_file = tmp_path / "policies.yaml"
    pol_file.write_text(
        "quiet_hours:\n"
        "  - start_hour: 8\n"
        "    end_hour: 22\n"
        "    blocked_tools: call_phone\n"
    )

    import pytest

    with pytest.raises(ValueError, match="blocked_tools"):
        Policy.from_file(pol_file)


def test_policy_schema_validation_rate_limits_non_positive_raises(tmp_path) -> None:
    pol_file = tmp_path / "policies.yaml"
    pol_file.write_text(
        "rate_limits:\n"
        "  - tool_pattern: payments\n"
        "    max_calls: 0\n"
        "    window_seconds: 60\n"
    )

    import pytest

    with pytest.raises(ValueError, match="must be > 0"):
        Policy.from_file(pol_file)


def test_policy_schema_validation_sandbox_profiles_wrong_type_raises(tmp_path) -> None:
    pol_file = tmp_path / "policies.yaml"
    pol_file.write_text(
        "sandbox_profiles: bad\n"
    )

    import pytest

    with pytest.raises(ValueError, match="sandbox_profiles"):
        Policy.from_file(pol_file)

