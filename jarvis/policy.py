"""Deterministic policy pre-flight check.

Runs BEFORE every tool call. NOT an LLM check — these are hardcoded rules
that don't get talked out of by clever prompts. Loaded from policies.yaml.

Phase 1 covers: blocked tools, blocked URL substrings, notes path traversal.
Phase 4+ adds spending caps, trading limits, calling windows.
"""
import datetime
import fnmatch
import shlex
import time
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

try:
    import yaml
except ImportError:
    yaml = None


POLICY_KEYS: set[str] = {
    # Core currently used by Policy.check_tool
    "blocked_tools",
    "tool_phase_requirements",
    "blocked_domains",
    "allowed_domains",
    "call_contact_allowlist",
    "critical_smart_home_entities",
    "smart_home_write_actions",
    "quiet_hours",
    "schedule_rules",
    "rate_limits",
    # Compatibility aliases kept explicit for config migration safety
    "phase_gates",
    "domain_blocks",
    "domain_allowlist",
    "notes_path_block",
    "critical_smart_home_patterns",
    "sandbox_profiles",
}


@dataclass
class PolicyDecision:
    allowed: bool
    reason: str = ""


@dataclass(frozen=True)
class QuietHoursRule:
    """Deny a set of tools outside the allowed hour window.

    ``start_hour`` and ``end_hour`` are 0-based 24-hour integers (0–23).
    The *allowed* window is ``[start_hour, end_hour)``; any call made *outside*
    that window and matching ``blocked_tools`` is denied.

    Example — block ``call_phone`` between 22:00 and 08:00::

        QuietHoursRule(start_hour=8, end_hour=22, blocked_tools=["call_phone"])
    """

    start_hour: int  # first hour of the ALLOWED window (inclusive)
    end_hour: int    # last hour of the ALLOWED window (exclusive)
    blocked_tools: tuple[str, ...] = field(default_factory=tuple)  # type: ignore[assignment]

    def is_quiet_now(self, now: datetime.datetime | None = None) -> bool:
        """Return True if the current time is outside the allowed window."""
        hour = (now or datetime.datetime.now()).hour
        if self.start_hour <= self.end_hour:
            # Normal range e.g. 8–22
            return not (self.start_hour <= hour < self.end_hour)
        else:
            # Overnight range e.g. 22–6 (wraps midnight)
            return not (hour >= self.start_hour or hour < self.end_hour)

    def denies(self, tool_name: str, now: datetime.datetime | None = None) -> bool:
        """Return True if this rule should block *tool_name* right now."""
        return bool(self.blocked_tools) and tool_name in self.blocked_tools and self.is_quiet_now(now)


@dataclass(frozen=True)
class RateLimitRule:
    """Deny a tool once it exceeds *max_calls* within a rolling *window_seconds* window."""

    tool_pattern: str   # exact tool name match
    max_calls: int
    window_seconds: int


@dataclass(frozen=True)
class ScheduleRule:
    """Deny selected tools on selected weekdays.

    Weekdays follow Python convention: Monday=0 ... Sunday=6.
    """

    weekdays: tuple[int, ...] = field(default_factory=tuple)
    blocked_tools: tuple[str, ...] = field(default_factory=tuple)

    def denies(self, tool_name: str, now: datetime.datetime | None = None) -> bool:
        dt = now or datetime.datetime.now()
        return bool(self.blocked_tools) and tool_name in self.blocked_tools and dt.weekday() in self.weekdays


@dataclass(frozen=True)
class PolicySchema:
    """Explicit policy-as-code schema for policies.yaml."""

    blocked_tools: tuple[str, ...] = field(default_factory=tuple)
    tool_phase_requirements: dict[str, str] = field(default_factory=dict)
    blocked_domains: tuple[str, ...] = field(default_factory=tuple)
    allowed_domains: tuple[str, ...] = field(default_factory=tuple)
    call_contact_allowlist: tuple[str, ...] = field(default_factory=tuple)
    critical_smart_home_entities: tuple[str, ...] = field(default_factory=tuple)
    smart_home_write_actions: tuple[str, ...] = field(default_factory=tuple)
    quiet_hours: tuple[QuietHoursRule, ...] = field(default_factory=tuple)
    schedule_rules: tuple[ScheduleRule, ...] = field(default_factory=tuple)
    rate_limits: tuple[RateLimitRule, ...] = field(default_factory=tuple)
    # Compatibility aliases for gradual migration
    phase_gates: dict[str, str] = field(default_factory=dict)
    domain_blocks: tuple[str, ...] = field(default_factory=tuple)
    domain_allowlist: tuple[str, ...] = field(default_factory=tuple)
    notes_path_block: bool = True
    critical_smart_home_patterns: tuple[str, ...] = field(default_factory=tuple)
    sandbox_profiles: dict[str, dict[str, Any]] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, raw: Any) -> "PolicySchema":
        if not isinstance(raw, dict):
            raise ValueError("policies.yaml must contain a top-level mapping")

        unknown_keys = sorted(k for k in raw.keys() if k not in POLICY_KEYS)
        if unknown_keys:
            raise ValueError(
                "unknown policy keys: " + ", ".join(str(k) for k in unknown_keys)
            )

        return cls(
            blocked_tools=cls._list_of_str(raw, "blocked_tools"),
            tool_phase_requirements=cls._dict_str_str(raw, "tool_phase_requirements"),
            blocked_domains=cls._list_of_str(raw, "blocked_domains"),
            allowed_domains=cls._list_of_str(raw, "allowed_domains"),
            call_contact_allowlist=cls._list_of_str(raw, "call_contact_allowlist"),
            critical_smart_home_entities=cls._list_of_str(raw, "critical_smart_home_entities"),
            smart_home_write_actions=cls._list_of_str(raw, "smart_home_write_actions"),
            quiet_hours=cls._parse_quiet_hours(raw.get("quiet_hours") or []),
            schedule_rules=cls._parse_schedule_rules(raw.get("schedule_rules") or []),
            rate_limits=cls._parse_rate_limits(raw.get("rate_limits") or []),
            phase_gates=cls._dict_str_str(raw, "phase_gates"),
            domain_blocks=cls._list_of_str(raw, "domain_blocks"),
            domain_allowlist=cls._list_of_str(raw, "domain_allowlist"),
            notes_path_block=cls._bool_value(raw, "notes_path_block", default=True),
            critical_smart_home_patterns=cls._list_of_str(raw, "critical_smart_home_patterns"),
            sandbox_profiles=cls._parse_sandbox_profiles(raw.get("sandbox_profiles") or {}),
        )

    def to_rules(self) -> dict[str, Any]:
        return {
            "blocked_tools": list(self.blocked_tools),
            "tool_phase_requirements": dict(self.tool_phase_requirements),
            "blocked_domains": list(self.blocked_domains),
            "allowed_domains": list(self.allowed_domains),
            "call_contact_allowlist": list(self.call_contact_allowlist),
            "critical_smart_home_entities": list(self.critical_smart_home_entities),
            "smart_home_write_actions": list(self.smart_home_write_actions),
            "quiet_hours": [
                {
                    "start_hour": r.start_hour,
                    "end_hour": r.end_hour,
                    "blocked_tools": list(r.blocked_tools),
                }
                for r in self.quiet_hours
            ],
            "schedule_rules": [
                {
                    "weekdays": list(r.weekdays),
                    "blocked_tools": list(r.blocked_tools),
                }
                for r in self.schedule_rules
            ],
            "rate_limits": [
                {
                    "tool_pattern": r.tool_pattern,
                    "max_calls": r.max_calls,
                    "window_seconds": r.window_seconds,
                }
                for r in self.rate_limits
            ],
            "phase_gates": dict(self.phase_gates),
            "domain_blocks": list(self.domain_blocks),
            "domain_allowlist": list(self.domain_allowlist),
            "notes_path_block": self.notes_path_block,
            "critical_smart_home_patterns": list(self.critical_smart_home_patterns),
            "sandbox_profiles": self.sandbox_profiles,
        }

    @staticmethod
    def _parse_sandbox_profiles(raw: Any) -> dict[str, dict[str, Any]]:
        if not isinstance(raw, dict):
            raise ValueError(
                f"policy key 'sandbox_profiles' has wrong type: expected dict, got {type(raw).__name__}"
            )

        out: dict[str, dict[str, Any]] = {}

        for tool_name in ("shell_run", "web_fetch"):
            cfg = raw.get(tool_name)
            if cfg is None:
                continue
            if not isinstance(cfg, dict):
                raise ValueError(
                    f"policy key 'sandbox_profiles.{tool_name}' has wrong type: expected dict, got {type(cfg).__name__}"
                )

            if tool_name == "shell_run":
                max_chars = cfg.get("max_command_chars", 0)
                if not isinstance(max_chars, int) or max_chars < 0:
                    raise ValueError(
                        "policy key 'sandbox_profiles.shell_run.max_command_chars' must be an integer >= 0"
                    )

                blocked_prefixes = cfg.get("blocked_prefixes", [])
                blocked_tokens = cfg.get("blocked_tokens", [])
                if not isinstance(blocked_prefixes, list) or not all(isinstance(x, str) for x in blocked_prefixes):
                    raise ValueError(
                        "policy key 'sandbox_profiles.shell_run.blocked_prefixes' must be a list of strings"
                    )
                if not isinstance(blocked_tokens, list) or not all(isinstance(x, str) for x in blocked_tokens):
                    raise ValueError(
                        "policy key 'sandbox_profiles.shell_run.blocked_tokens' must be a list of strings"
                    )

                out[tool_name] = {
                    "max_command_chars": max_chars,
                    "blocked_prefixes": [x.strip() for x in blocked_prefixes if x.strip()],
                    "blocked_tokens": [x.strip() for x in blocked_tokens if x.strip()],
                }

            if tool_name == "web_fetch":
                max_chars_cap = cfg.get("max_chars_cap", 0)
                if not isinstance(max_chars_cap, int) or max_chars_cap < 0:
                    raise ValueError(
                        "policy key 'sandbox_profiles.web_fetch.max_chars_cap' must be an integer >= 0"
                    )

                blocked_hosts = cfg.get("blocked_hosts", [])
                if not isinstance(blocked_hosts, list) or not all(isinstance(x, str) for x in blocked_hosts):
                    raise ValueError(
                        "policy key 'sandbox_profiles.web_fetch.blocked_hosts' must be a list of strings"
                    )

                out[tool_name] = {
                    "max_chars_cap": max_chars_cap,
                    "blocked_hosts": [x.strip().lower() for x in blocked_hosts if x.strip()],
                }

        return out

    @staticmethod
    def _list_of_str(raw: dict[str, Any], key: str) -> tuple[str, ...]:
        value = raw.get(key, [])
        if not isinstance(value, list):
            raise ValueError(f"policy key '{key}' has wrong type: expected list, got {type(value).__name__}")
        out: list[str] = []
        for idx, item in enumerate(value):
            if not isinstance(item, str):
                raise ValueError(f"policy key '{key}[{idx}]' must be a string")
            if item.strip():
                out.append(item.strip())
        return tuple(out)

    @staticmethod
    def _dict_str_str(raw: dict[str, Any], key: str) -> dict[str, str]:
        value = raw.get(key, {})
        if not isinstance(value, dict):
            raise ValueError(f"policy key '{key}' has wrong type: expected dict, got {type(value).__name__}")
        out: dict[str, str] = {}
        for k, v in value.items():
            if not isinstance(k, str) or not isinstance(v, str):
                raise ValueError(f"policy key '{key}' must map string keys to string values")
            if k.strip() and v.strip():
                out[k.strip()] = v.strip()
        return out

    @staticmethod
    def _bool_value(raw: dict[str, Any], key: str, default: bool) -> bool:
        value = raw.get(key, default)
        if not isinstance(value, bool):
            raise ValueError(f"policy key '{key}' has wrong type: expected bool, got {type(value).__name__}")
        return value

    @staticmethod
    def _parse_quiet_hours(entries: Any) -> tuple[QuietHoursRule, ...]:
        if not isinstance(entries, list):
            raise ValueError(f"policy key 'quiet_hours' has wrong type: expected list, got {type(entries).__name__}")
        rules: list[QuietHoursRule] = []
        for idx, entry in enumerate(entries):
            if not isinstance(entry, dict):
                raise ValueError(f"policy key 'quiet_hours[{idx}]' must be a mapping")
            try:
                start_hour = int(entry["start_hour"])
                end_hour = int(entry["end_hour"])
                blocked_tools = entry.get("blocked_tools") or []
            except (KeyError, TypeError, ValueError):
                raise ValueError(f"policy key 'quiet_hours[{idx}]' is invalid")

            if not (0 <= start_hour <= 23 and 0 <= end_hour <= 23):
                raise ValueError(f"policy key 'quiet_hours[{idx}]' hours must be in range 0..23")
            if not isinstance(blocked_tools, list) or not all(isinstance(x, str) for x in blocked_tools):
                raise ValueError(f"policy key 'quiet_hours[{idx}].blocked_tools' must be a list of strings")

            rules.append(
                QuietHoursRule(
                    start_hour=start_hour,
                    end_hour=end_hour,
                    blocked_tools=tuple(x.strip() for x in blocked_tools if x.strip()),
                )
            )
        return tuple(rules)

    @staticmethod
    def _parse_rate_limits(entries: Any) -> tuple[RateLimitRule, ...]:
        if not isinstance(entries, list):
            raise ValueError(f"policy key 'rate_limits' has wrong type: expected list, got {type(entries).__name__}")
        rules: list[RateLimitRule] = []
        for idx, entry in enumerate(entries):
            if not isinstance(entry, dict):
                raise ValueError(f"policy key 'rate_limits[{idx}]' must be a mapping")
            try:
                tool_pattern = str(entry["tool_pattern"]).strip()
                max_calls = int(entry["max_calls"])
                window_seconds = int(entry["window_seconds"])
            except (KeyError, TypeError, ValueError):
                raise ValueError(f"policy key 'rate_limits[{idx}]' is invalid")

            if not tool_pattern:
                raise ValueError(f"policy key 'rate_limits[{idx}].tool_pattern' must not be empty")
            if max_calls <= 0 or window_seconds <= 0:
                raise ValueError(f"policy key 'rate_limits[{idx}]' max_calls/window_seconds must be > 0")

            rules.append(
                RateLimitRule(
                    tool_pattern=tool_pattern,
                    max_calls=max_calls,
                    window_seconds=window_seconds,
                )
            )
        return tuple(rules)

    @staticmethod
    def _parse_schedule_rules(entries: Any) -> tuple[ScheduleRule, ...]:
        if not isinstance(entries, list):
            raise ValueError(f"policy key 'schedule_rules' has wrong type: expected list, got {type(entries).__name__}")
        rules: list[ScheduleRule] = []
        for idx, entry in enumerate(entries):
            if not isinstance(entry, dict):
                raise ValueError(f"policy key 'schedule_rules[{idx}]' must be a mapping")

            weekdays = entry.get("weekdays") or []
            blocked_tools = entry.get("blocked_tools") or []

            if not isinstance(weekdays, list) or not all(isinstance(d, int) for d in weekdays):
                raise ValueError(f"policy key 'schedule_rules[{idx}].weekdays' must be a list of integers")
            if not weekdays:
                raise ValueError(f"policy key 'schedule_rules[{idx}].weekdays' must not be empty")
            if any(d < 0 or d > 6 for d in weekdays):
                raise ValueError(f"policy key 'schedule_rules[{idx}].weekdays' values must be in range 0..6")
            if not isinstance(blocked_tools, list) or not all(isinstance(t, str) for t in blocked_tools):
                raise ValueError(f"policy key 'schedule_rules[{idx}].blocked_tools' must be a list of strings")

            rules.append(
                ScheduleRule(
                    weekdays=tuple(weekdays),
                    blocked_tools=tuple(t.strip() for t in blocked_tools if t.strip()),
                )
            )
        return tuple(rules)


class PolicyRateLimiter:
    """In-memory sliding-window rate limiter keyed by tool name."""

    def __init__(self, rules: list[RateLimitRule]) -> None:
        self._rules = rules
        self._history: dict[str, deque[float]] = {}

    def check(self, tool_name: str, _now: float | None = None) -> tuple[bool, str]:
        """Return ``(allowed, reason)``.  *_now* is injectable for tests."""
        now = _now if _now is not None else time.monotonic()
        for rule in self._rules:
            if rule.tool_pattern != tool_name:
                continue
            bucket = self._history.setdefault(tool_name, deque())
            cutoff = now - rule.window_seconds
            while bucket and bucket[0] < cutoff:
                bucket.popleft()
            if len(bucket) >= rule.max_calls:
                return (
                    False,
                    f"tool '{tool_name}' exceeded rate limit "
                    f"({rule.max_calls} calls / {rule.window_seconds}s)",
                )
            bucket.append(now)
        return (True, "")


@dataclass
class Policy:
    rules: dict = field(default_factory=dict)
    enabled_phases: set[str] = field(default_factory=set)
    quiet_hours_rules: list[QuietHoursRule] = field(default_factory=list)
    schedule_rules: list[ScheduleRule] = field(default_factory=list)
    rate_limiter: PolicyRateLimiter = field(default_factory=lambda: PolicyRateLimiter([]))

    @classmethod
    def from_file(
        cls,
        path: Path,
        enabled_phases: set[str] | None = None,
    ) -> "Policy":
        path = Path(path)
        if not path.exists() or yaml is None:
            return cls(rules={}, enabled_phases=enabled_phases or set())
        with open(path) as f:
            raw = yaml.safe_load(f) or {}
        schema = PolicySchema.from_dict(raw)
        rules = schema.to_rules()
        quiet_hours_rules = list(schema.quiet_hours)
        schedule_rules = list(schema.schedule_rules)
        rate_limiter = PolicyRateLimiter(list(schema.rate_limits))
        return cls(
            rules=rules,
            enabled_phases=enabled_phases or set(),
            quiet_hours_rules=quiet_hours_rules,
            schedule_rules=schedule_rules,
            rate_limiter=rate_limiter,
        )

    @staticmethod
    def _parse_quiet_hours(entries: list) -> list[QuietHoursRule]:
        return list(PolicySchema._parse_quiet_hours(entries))

    @staticmethod
    def _validate_schema(rules: Any) -> None:
        PolicySchema.from_dict(rules)

    @staticmethod
    def _parse_rate_limits(entries: list) -> list[RateLimitRule]:
        return list(PolicySchema._parse_rate_limits(entries))

    def check_tool(self, tool_name: str, args: dict[str, Any], _now: datetime.datetime | None = None) -> PolicyDecision:
        # Blocked tools
        blocked = self.rules.get("blocked_tools") or []
        if tool_name in blocked:
            return PolicyDecision(False, f"tool '{tool_name}' is in blocked_tools")

        # Quiet-hours enforcement
        for rule in self.quiet_hours_rules:
            if rule.denies(tool_name, _now):
                return PolicyDecision(
                    False,
                    f"tool '{tool_name}' is blocked during quiet hours "
                    f"(allowed {rule.start_hour:02d}:00–{rule.end_hour:02d}:00)",
                )

        # Schedule-based restrictions (e.g. no weekend spend).
        for rule in self.schedule_rules:
            if rule.denies(tool_name, _now):
                weekday = (_now or datetime.datetime.now()).weekday()
                return PolicyDecision(
                    False,
                    f"tool '{tool_name}' is blocked by schedule rule on weekday {weekday}",
                )

        # Rate-limit enforcement
        rl_allowed, rl_reason = self.rate_limiter.check(tool_name)
        if not rl_allowed:
            return PolicyDecision(False, rl_reason)

        # Phase gating for tools not yet enabled in this deployment.
        required_phase = (self.rules.get("tool_phase_requirements") or {}).get(
            tool_name
        )
        if required_phase and required_phase not in self.enabled_phases:
            return PolicyDecision(
                False,
                f"tool '{tool_name}' requires phase '{required_phase}'",
            )

        # Sandbox profile definitions for command/web execution tools.
        sandbox_profiles = self.rules.get("sandbox_profiles") or {}
        if tool_name == "shell_run":
            shell_profile = sandbox_profiles.get("shell_run") or {}
            command = str(args.get("command") or "")
            command_lc = command.strip().lower()

            max_command_chars = int(shell_profile.get("max_command_chars") or 0)
            if max_command_chars > 0 and len(command) > max_command_chars:
                return PolicyDecision(
                    False,
                    f"shell_run command exceeds sandbox profile limit ({max_command_chars} chars)",
                )

            for prefix in shell_profile.get("blocked_prefixes") or []:
                p = str(prefix).strip().lower()
                if p and command_lc.startswith(p):
                    return PolicyDecision(
                        False,
                        f"shell_run command blocked by sandbox profile prefix '{p}'",
                    )

            tokens: list[str]
            try:
                tokens = [t.lower() for t in shlex.split(command)]
            except ValueError:
                tokens = [t.lower() for t in command.split()]

            for token in shell_profile.get("blocked_tokens") or []:
                tok = str(token).strip().lower()
                if tok and tok in tokens:
                    return PolicyDecision(
                        False,
                        f"shell_run command blocked by sandbox profile token '{tok}'",
                    )

        if tool_name == "web_fetch":
            web_profile = sandbox_profiles.get("web_fetch") or {}

            requested_max_chars = args.get("max_chars")
            max_chars_cap = int(web_profile.get("max_chars_cap") or 0)
            if isinstance(requested_max_chars, int) and max_chars_cap > 0 and requested_max_chars > max_chars_cap:
                return PolicyDecision(
                    False,
                    f"web_fetch max_chars exceeds sandbox profile cap ({max_chars_cap})",
                )

            blocked_hosts = [str(x).strip().lower() for x in (web_profile.get("blocked_hosts") or []) if str(x).strip()]
            for target in self._extract_domain_targets(args):
                lowered = target.lower()
                if any(host in lowered for host in blocked_hosts):
                    return PolicyDecision(False, "web_fetch target blocked by sandbox profile")

        # Global domain allow/deny checks for URL/domain-like args.
        blocked_domains = [
            item.strip().lower()
            for item in (
                (self.rules.get("blocked_domains") or [])
                + (self.rules.get("domain_blocks") or [])
            )
            if isinstance(item, str) and item.strip()
        ]
        allowed_domains = [
            item.strip().lower()
            for item in (
                (self.rules.get("allowed_domains") or [])
                + (self.rules.get("domain_allowlist") or [])
            )
            if isinstance(item, str) and item.strip()
        ]
        for target in self._extract_domain_targets(args):
            lowered = target.lower()
            for dom in blocked_domains:
                if dom in lowered:
                    return PolicyDecision(False, f"contains blocked domain '{dom}'")
            if allowed_domains and not any(dom in lowered for dom in allowed_domains):
                return PolicyDecision(
                    False,
                    "target is outside allowed_domains allowlist",
                )

        # Telephony contact allowlist check.
        if tool_name in {"call_phone", "reservation_call"}:
            call_contact_allowlist = [
                item.strip()
                for item in (self.rules.get("call_contact_allowlist") or [])
                if isinstance(item, str) and item.strip()
            ]
            if call_contact_allowlist:
                phone_number = str(args.get("phone_number") or "").strip()
                if not phone_number:
                    return PolicyDecision(False, f"{tool_name} requires phone_number for allowlist check")
                if not any(fnmatch.fnmatch(phone_number, pattern) for pattern in call_contact_allowlist):
                    return PolicyDecision(
                        False,
                        "phone_number is outside call_contact_allowlist",
                    )

        # Global path-traversal/absolute-path guard for path-like args.
        if bool(self.rules.get("notes_path_block", True)):
            bad_path = self._find_unsafe_path(args)
            if bad_path is not None:
                return PolicyDecision(
                    False,
                    f"unsafe path '{bad_path}' is not allowed",
                )

        # Notes write requires a non-empty relative path.
        if tool_name == "notes_write":
            path = args.get("path", "")
            if not isinstance(path, str) or not path.strip():
                return PolicyDecision(
                    False,
                    "notes path must be a non-empty relative path",
                )

        # Smart-home writes for critical entities require approval-oriented flows.
        if tool_name == "home_assistant" and self._is_smart_home_write(args):
            critical = self.rules.get("critical_smart_home_entities") or []
            for entity_id in self._extract_entity_ids(args):
                if self._entity_matches_any(entity_id, critical):
                    return PolicyDecision(
                        False,
                        f"critical smart-home entity '{entity_id}' requires gated approval",
                    )

        return PolicyDecision(True)

    @staticmethod
    def _extract_domain_targets(args: dict[str, Any]) -> list[str]:
        """Extract URL/domain-like targets from structured tool arguments."""
        targets: list[str] = []
        domain_keys = {
            "url",
            "urls",
            "query",
            "queries",
            "domain",
            "domains",
            "host",
            "hostname",
        }

        def _walk(obj: Any, key_hint: str = "") -> None:
            if isinstance(obj, dict):
                for key, value in obj.items():
                    _walk(value, str(key).strip().lower())
                return
            if isinstance(obj, list):
                for value in obj:
                    _walk(value, key_hint)
                return
            if not isinstance(obj, str):
                return

            value = obj.strip()
            if not value:
                return

            if key_hint in domain_keys or "url" in key_hint or "domain" in key_hint:
                parsed = urlparse(value)
                if parsed.netloc:
                    targets.append(parsed.netloc)
                else:
                    targets.append(value)

        _walk(args)
        return targets

    @staticmethod
    def _find_unsafe_path(args: dict[str, Any]) -> str | None:
        """Return first unsafe path-like string found in args, else None."""
        path_key_markers = {"path", "file", "filepath", "filename", "directory", "dir"}

        def _is_pathlike_key(key: str) -> bool:
            return any(marker in key for marker in path_key_markers)

        def _is_unsafe(path_value: str) -> bool:
            value = path_value.strip()
            if not value:
                return False
            if value.startswith("/") or value.startswith("~"):
                return True
            if len(value) >= 3 and value[1] == ":" and value[2] in {"\\", "/"}:
                return True
            parts = [p for p in value.replace("\\", "/").split("/") if p]
            return any(part == ".." for part in parts)

        def _walk(obj: Any, key_hint: str = "") -> str | None:
            if isinstance(obj, dict):
                for key, value in obj.items():
                    bad = _walk(value, str(key).strip().lower())
                    if bad is not None:
                        return bad
                return None
            if isinstance(obj, list):
                for value in obj:
                    bad = _walk(value, key_hint)
                    if bad is not None:
                        return bad
                return None
            if isinstance(obj, str) and _is_pathlike_key(key_hint) and _is_unsafe(obj):
                return obj
            return None

        return _walk(args)

    @staticmethod
    def _extract_entity_ids(args: dict[str, Any]) -> list[str]:
        values: list[str] = []

        def _append(raw: Any) -> None:
            if isinstance(raw, str) and raw.strip():
                values.append(raw.strip())
            elif isinstance(raw, list):
                for item in raw:
                    if isinstance(item, str) and item.strip():
                        values.append(item.strip())

        _append(args.get("entity_id"))
        _append(args.get("entity_ids"))

        service_data = args.get("service_data")
        if isinstance(service_data, dict):
            _append(service_data.get("entity_id"))
            _append(service_data.get("entity_ids"))

        return values

    def _is_smart_home_write(self, args: dict[str, Any]) -> bool:
        action = str(
            args.get("action")
            or args.get("operation")
            or args.get("service")
            or ""
        ).strip().lower()

        if action in {"read", "get_state", "list_entities", "history", "get_history"}:
            return False

        write_actions = {
            item.strip().lower()
            for item in (self.rules.get("smart_home_write_actions") or [])
            if isinstance(item, str) and item.strip()
        }
        if not write_actions:
            write_actions = {
                "turn_on",
                "turn_off",
                "toggle",
                "lock",
                "unlock",
                "open",
                "close",
                "arm",
                "disarm",
                "set_temperature",
                "call_service",
            }

        if action:
            return action in write_actions

        # Fallback: service-style payloads are considered mutating by default.
        return "service" in args or "service_data" in args

    @staticmethod
    def _entity_matches_any(entity_id: str, patterns: list[Any]) -> bool:
        for pattern in patterns:
            if not isinstance(pattern, str):
                continue
            candidate = pattern.strip().lower()
            if not candidate:
                continue
            if candidate.endswith("*"):
                if entity_id.lower().startswith(candidate[:-1]):
                    return True
            elif entity_id.lower() == candidate:
                return True
        return False
