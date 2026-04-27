"""Structured runtime error types.

Every error that can escape the dispatch boundary has a canonical typed form.
Callers can inspect the ``kind`` discriminant without parsing strings.

Kinds
-----
``policy-denied``       — policy preflight blocked the tool call.
``policy-rate-limited`` — tool call exceeded the configured rate limit.
``tool-not-found``      — the registry has no handler for the requested tool name.
``tool-failure``    — the tool handler raised an unexpected exception.
``tool-bad-args``   — the tool handler raised ``TypeError`` (wrong signature).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


RuntimeErrorKind = Literal[
    "policy-denied",
    "policy-rate-limited",
    "tool-not-found",
    "tool-failure",
    "tool-bad-args",
]


@dataclass(frozen=True)
class RuntimeToolError:
    """A structured, typed error returned by the dispatch boundary."""

    kind: RuntimeErrorKind
    tool_name: str
    message: str
    detail: str = ""

    def to_dict(self) -> dict[str, str]:
        return {
            "error": self.kind,
            "tool_name": self.tool_name,
            "message": self.message,
            "detail": self.detail,
        }
