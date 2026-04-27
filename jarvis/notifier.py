"""Push notifier adapters for approval alerts.

Architecture
------------
``PushNotifier`` is the abstract interface.  Concrete adapters:

* ``NtfyNotifier``   — sends HTTP POST to an ntfy.sh topic (or self-hosted).
* ``LogNotifier``    — structured-log only (no outbound call), used as fallback
                       when the channel is disabled or unconfigured.

Usage
-----
Build via ``build_notifier(config)`` which picks the right adapter based on
``config.approval_channel``.

ntfy setup
----------
1. Install ntfy app on your phone (ntfy.sh).
2. Subscribe to a topic (e.g. ``jarvis-approvals``).
3. Set env vars::

       JARVIS_NTFY_TOPIC=jarvis-approvals
       JARVIS_NTFY_URL=https://ntfy.sh          # default; swap for self-hosted
       JARVIS_NTFY_PRIORITY=high                # default
       JARVIS_NTFY_TOKEN=                       # optional Bearer token

4. Set ``JARVIS_APPROVAL_CHANNEL=ntfy``.

Message format
--------------
Title:   "Jarvis approval request [<risk_tier>]"
Body:    "{action or kind}: {one-line summary}"
Tags:    "warning,robot"  (+ "skull" for critical tier)
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .approval import ApprovalEnvelope

try:
    import httpx as httpx  # noqa: PLC0414  (module-level for mockability)
except ImportError:
    httpx = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

_DEFAULT_NTFY_URL = "https://ntfy.sh"
_DEFAULT_PRIORITY = "high"


# ── abstract interface ─────────────────────────────────────────────────────────


class PushNotifier(ABC):
    """Send a push notification for an approval request."""

    @abstractmethod
    def notify(
        self,
        approval_id: str,
        kind: str,
        payload: dict[str, Any],
        envelope: "ApprovalEnvelope | None" = None,
    ) -> dict[str, Any]:
        """Send notification.  Returns ``{"sent": bool, ...}``."""


# ── log-only fallback ──────────────────────────────────────────────────────────


class LogNotifier(PushNotifier):
    """No-op notifier — logs the event but sends no push notification."""

    def notify(
        self,
        approval_id: str,
        kind: str,
        payload: dict[str, Any],
        envelope: "ApprovalEnvelope | None" = None,
    ) -> dict[str, Any]:
        logger.info(
            "approval_notification (log-only): id=%s kind=%s risk_tier=%s",
            approval_id,
            kind,
            envelope.risk_tier if envelope else "medium",
        )
        return {"sent": False, "channel": "log"}


# ── ntfy adapter ───────────────────────────────────────────────────────────────


class NtfyNotifier(PushNotifier):
    """Send push notifications via ntfy.sh (or self-hosted ntfy).

    Parameters
    ----------
    topic:
        ntfy topic string (e.g. ``jarvis-approvals``).
    ntfy_url:
        Base URL of the ntfy server (default: ``https://ntfy.sh``).
    priority:
        ntfy priority label: ``min``, ``low``, ``default``, ``high``, ``urgent``.
    token:
        Optional Bearer token for authenticated topics.
    """

    def __init__(
        self,
        topic: str,
        ntfy_url: str = _DEFAULT_NTFY_URL,
        priority: str = _DEFAULT_PRIORITY,
        token: str = "",
    ) -> None:
        self._topic = topic.strip()
        self._ntfy_url = ntfy_url.rstrip("/")
        self._priority = priority.strip() or _DEFAULT_PRIORITY
        self._token = token.strip()

    # ── helpers ────────────────────────────────────────────────────────────────

    def _build_message(
        self,
        kind: str,
        payload: dict[str, Any],
        envelope: "ApprovalEnvelope | None" = None,
    ) -> str:
        """One-line summary of the approval payload."""
        # Use envelope.action as the lead-in when available
        lead = (envelope.action.strip() if envelope and envelope.action.strip() else kind)

        parts: list[str] = []
        for key in ("action", "tool", "recipient", "channel", "entity_id", "amount"):
            value = payload.get(key)
            if value:
                parts.append(f"{key}={value}")
        if not parts:
            keys = list(payload.keys())[:3]
            parts = [f"{k}={payload[k]}" for k in keys]

        # Append budget impact when non-zero
        if envelope and envelope.budget_impact > 0:
            parts.append(f"budget_impact=${envelope.budget_impact:.2f}")

        # Append reason when present
        if envelope and envelope.reason.strip():
            parts.append(f"reason={envelope.reason.strip()[:80]}")

        summary = ", ".join(str(p) for p in parts)
        return f"{lead}: {summary}" if summary else lead

    def _build_title(self, envelope: "ApprovalEnvelope | None" = None) -> str:
        tier = (envelope.risk_tier if envelope else "medium") or "medium"
        return f"Jarvis approval [{tier}]"

    def _build_tags(self, envelope: "ApprovalEnvelope | None" = None) -> str:
        tier = (envelope.risk_tier if envelope else "medium") or "medium"
        base = "warning,robot"
        return base + ",skull" if tier == "critical" else base

    def _build_headers(self, envelope: "ApprovalEnvelope | None" = None) -> dict[str, str]:
        headers: dict[str, str] = {
            "Title": self._build_title(envelope),
            "Priority": self._priority,
            "Tags": self._build_tags(envelope),
        }
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    # ── PushNotifier protocol ──────────────────────────────────────────────────

    def notify(
        self,
        approval_id: str,
        kind: str,
        payload: dict[str, Any],
        envelope: "ApprovalEnvelope | None" = None,
    ) -> dict[str, Any]:
        if not self._topic:
            logger.warning("ntfy topic is empty — skipping push notification")
            return {"sent": False, "channel": "ntfy", "reason": "no_topic"}

        if httpx is None:
            logger.warning("httpx not installed — ntfy notification skipped")
            return {"sent": False, "channel": "ntfy", "reason": "httpx_missing"}

        url = f"{self._ntfy_url}/{self._topic}"
        message = self._build_message(kind, payload, envelope)
        headers = self._build_headers(envelope)

        try:
            resp = httpx.post(
                url,
                content=message.encode(),
                headers=headers,
                timeout=8.0,
            )
            resp.raise_for_status()
            logger.info(
                "ntfy notification sent: approval_id=%s topic=%s status=%s",
                approval_id,
                self._topic,
                resp.status_code,
            )
            return {
                "sent": True,
                "channel": "ntfy",
                "topic": self._topic,
                "status_code": resp.status_code,
            }
        except Exception as exc:
            logger.warning("ntfy notification failed: %s", exc)
            return {"sent": False, "channel": "ntfy", "error": str(exc)}


# ── factory ────────────────────────────────────────────────────────────────────


def build_notifier(
    channel: str,
    ntfy_topic: str = "",
    ntfy_url: str = _DEFAULT_NTFY_URL,
    ntfy_priority: str = _DEFAULT_PRIORITY,
    ntfy_token: str = "",
) -> PushNotifier:
    """Return the appropriate ``PushNotifier`` for the configured channel.

    Parameters
    ----------
    channel:
        ``"ntfy"`` or any other string (falls back to ``LogNotifier``).
    ntfy_topic:
        Topic to use when channel is ``"ntfy"``.
    ntfy_url:
        ntfy server base URL.
    ntfy_priority:
        ntfy message priority.
    ntfy_token:
        Optional Bearer token for authenticated ntfy topics.
    """
    if channel == "ntfy":
        if not ntfy_topic:
            logger.warning(
                "JARVIS_NTFY_TOPIC not set — ntfy notifications disabled, "
                "falling back to log-only notifier"
            )
            return LogNotifier()
        return NtfyNotifier(
            topic=ntfy_topic,
            ntfy_url=ntfy_url,
            priority=ntfy_priority,
            token=ntfy_token,
        )
    # unknown / disabled channel
    return LogNotifier()
