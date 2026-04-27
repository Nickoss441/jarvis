"""Persistent approval queue for gated actions."""
import json
import sqlite3
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# ── risk tiers ─────────────────────────────────────────────────────────────────

RISK_TIERS = {"low", "medium", "high", "critical"}

_DEFAULT_TTL_BY_TIER: dict[str, int] = {
    "low": 3600,      # 1 hour
    "medium": 900,    # 15 min
    "high": 300,      # 5 min
    "critical": 60,   # 1 min
}


# ── approval envelope ──────────────────────────────────────────────────────────


@dataclass
class ApprovalEnvelope:
    """Structured metadata attached to every approval request.

    Fields
    ------
    action:
        Human-readable verb describing what the agent wants to do
        (e.g. "Send Slack message to #ops", "Transfer $50 to vendor").
    reason:
        Why the agent is requesting this action — LLM-generated or
        caller-supplied justification string.
    budget_impact:
        Estimated monetary impact in USD (0.0 for non-financial actions).
    ttl_seconds:
        Seconds until this approval expires (0 = use config default).
    risk_tier:
        One of "low", "medium", "high", "critical".
        Drives notifier priority and cooldown rules.
    """

    action: str = ""
    reason: str = ""
    budget_impact: float = 0.0
    ttl_seconds: int = 0
    risk_tier: str = "medium"

    def __post_init__(self) -> None:
        self.risk_tier = self.risk_tier.strip().lower() or "medium"
        if self.risk_tier not in RISK_TIERS:
            self.risk_tier = "medium"
        self.budget_impact = max(0.0, float(self.budget_impact))
        self.ttl_seconds = max(0, int(self.ttl_seconds))
        if self.ttl_seconds == 0:
            self.ttl_seconds = _DEFAULT_TTL_BY_TIER.get(self.risk_tier, 900)

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "reason": self.reason,
            "budget_impact": self.budget_impact,
            "ttl_seconds": self.ttl_seconds,
            "risk_tier": self.risk_tier,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "ApprovalEnvelope":
        return cls(
            action=d.get("action", ""),
            reason=d.get("reason", ""),
            budget_impact=float(d.get("budget_impact", 0.0)),
            ttl_seconds=int(d.get("ttl_seconds", 0)),
            risk_tier=str(d.get("risk_tier", "medium")),
        )


class ApprovalStore:
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as con:
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS approvals (
                    id TEXT PRIMARY KEY,
                    ts REAL NOT NULL,
                    correlation_id TEXT,
                    kind TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    status TEXT NOT NULL,
                    decision_ts REAL,
                    decision_reason TEXT,
                    dispatch_ts REAL,
                    dispatch_result TEXT
                )
                """
            )
            cols = {
                row[1]
                for row in con.execute("PRAGMA table_info(approvals)").fetchall()
            }
            if "correlation_id" not in cols:
                con.execute("ALTER TABLE approvals ADD COLUMN correlation_id TEXT")
            # Envelope schema columns (additive migration)
            for col, default in [
                ("action", "''"),
                ("reason", "''"),
                ("budget_impact", "0.0"),
                ("ttl_seconds", "0"),
                ("risk_tier", "'medium'"),
            ]:
                if col not in cols:
                    con.execute(
                        f"ALTER TABLE approvals ADD COLUMN {col} TEXT DEFAULT {default}"
                    )
            con.execute(
                "CREATE INDEX IF NOT EXISTS approvals_status_idx ON approvals(status)"
            )

    def request(
        self,
        kind: str,
        payload: dict[str, Any],
        created_ts: float | None = None,
        correlation_id: str | None = None,
        envelope: "ApprovalEnvelope | None" = None,
    ) -> str:
        approval_id = str(uuid.uuid4())
        corr = correlation_id or str(uuid.uuid4())
        ts = time.time() if created_ts is None else created_ts
        env = envelope or ApprovalEnvelope()
        with sqlite3.connect(self.db_path) as con:
            con.execute(
                """
                INSERT INTO approvals
                    (id, ts, correlation_id, kind, payload, status,
                     action, reason, budget_impact, ttl_seconds, risk_tier)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    approval_id,
                    ts,
                    corr,
                    kind,
                    json.dumps(payload, sort_keys=True),
                    "pending",
                    env.action,
                    env.reason,
                    env.budget_impact,
                    env.ttl_seconds,
                    env.risk_tier,
                ),
            )
        return approval_id

    def get(self, approval_id: str) -> dict[str, Any] | None:
        with sqlite3.connect(self.db_path) as con:
            row = con.execute(
                """
                SELECT id, ts, kind, payload, status, decision_ts,
                      decision_reason, dispatch_ts, dispatch_result,
                      correlation_id,
                      action, reason, budget_impact, ttl_seconds, risk_tier
                FROM approvals
                WHERE id = ?
                """,
                (approval_id,),
            ).fetchone()
        if not row:
            return None
        return {
            "id": row[0],
            "ts": row[1],
            "kind": row[2],
            "payload": json.loads(row[3]),
            "status": row[4],
            "decision_ts": row[5],
            "decision_reason": row[6] or "",
            "dispatch_ts": row[7],
            "dispatch_result": json.loads(row[8]) if row[8] else None,
            "correlation_id": row[9] or "",
            "action": row[10] or "",
            "reason": row[11] or "",
            "budget_impact": float(row[12] or 0.0),
            "ttl_seconds": int(row[13] or 0),
            "risk_tier": row[14] or "medium",
        }

    def list_pending(self, limit: int = 50) -> list[dict[str, Any]]:
        return self._list_by_status("pending", limit)

    def list_approved(self, limit: int = 50) -> list[dict[str, Any]]:
        return self._list_by_status("approved", limit)

    def last_dispatch_ts(self) -> float | None:
        with sqlite3.connect(self.db_path) as con:
            row = con.execute(
                "SELECT MAX(dispatch_ts) FROM approvals WHERE dispatch_ts IS NOT NULL"
            ).fetchone()
        if not row or row[0] is None:
            return None
        return float(row[0])

    def last_dispatch_ts_for_kind(self, kind: str) -> float | None:
        with sqlite3.connect(self.db_path) as con:
            row = con.execute(
                """
                SELECT MAX(dispatch_ts)
                FROM approvals
                WHERE dispatch_ts IS NOT NULL AND kind = ?
                """,
                (kind,),
            ).fetchone()
        if not row or row[0] is None:
            return None
        return float(row[0])

    def _list_by_status(self, status: str, limit: int) -> list[dict[str, Any]]:
        with sqlite3.connect(self.db_path) as con:
            rows = con.execute(
                """
                SELECT id, ts, kind, payload, status, decision_ts,
                      decision_reason, dispatch_ts, dispatch_result,
                      correlation_id,
                      action, reason, budget_impact, ttl_seconds, risk_tier
                FROM approvals
                WHERE status = ?
                ORDER BY ts ASC
                LIMIT ?
                """,
                (status, limit),
            ).fetchall()
        return [
            {
                "id": r[0],
                "ts": r[1],
                "kind": r[2],
                "payload": json.loads(r[3]),
                "status": r[4],
                "decision_ts": r[5],
                "decision_reason": r[6] or "",
                "dispatch_ts": r[7],
                "dispatch_result": json.loads(r[8]) if r[8] else None,
                "correlation_id": r[9] or "",
                "action": r[10] or "",
                "reason": r[11] or "",
                "budget_impact": float(r[12] or 0.0),
                "ttl_seconds": int(r[13] or 0),
                "risk_tier": r[14] or "medium",
            }
            for r in rows
        ]

    def approve(self, approval_id: str, reason: str = "") -> bool:
        return self._set_decision(approval_id, "approved", reason)

    def reject(self, approval_id: str, reason: str = "") -> bool:
        return self._set_decision(approval_id, "rejected", reason)

    def edit_pending(
        self,
        approval_id: str,
        payload: dict[str, Any],
        envelope: ApprovalEnvelope,
    ) -> bool:
        """Edit a pending approval's payload and envelope fields."""
        with sqlite3.connect(self.db_path) as con:
            cur = con.execute(
                """
                UPDATE approvals
                SET payload = ?,
                    action = ?,
                    reason = ?,
                    budget_impact = ?,
                    ttl_seconds = ?,
                    risk_tier = ?
                WHERE id = ? AND status = 'pending'
                """,
                (
                    json.dumps(payload, sort_keys=True),
                    envelope.action,
                    envelope.reason,
                    envelope.budget_impact,
                    envelope.ttl_seconds,
                    envelope.risk_tier,
                    approval_id,
                ),
            )
            return cur.rowcount == 1

    def _set_decision(self, approval_id: str, status: str, reason: str) -> bool:
        with sqlite3.connect(self.db_path) as con:
            cur = con.execute(
                """
                UPDATE approvals
                SET status = ?, decision_ts = ?, decision_reason = ?
                WHERE id = ? AND status = 'pending'
                """,
                (status, time.time(), reason, approval_id),
            )
            return cur.rowcount == 1

    def expire_pending(self, ttl_seconds: int, reason: str = "expired: ttl exceeded") -> int:
        """Auto-deny pending items older than the provided TTL."""
        return len(self.expire_pending_ids(ttl_seconds=ttl_seconds, reason=reason))

    def expire_pending_ids(
        self,
        ttl_seconds: int,
        reason: str = "expired: ttl exceeded",
    ) -> list[str]:
        """Auto-deny stale pending items and return the expired approval IDs."""
        if ttl_seconds <= 0:
            return []

        cutoff = time.time() - ttl_seconds
        with sqlite3.connect(self.db_path) as con:
            rows = con.execute(
                "SELECT id FROM approvals WHERE status = 'pending' AND ts < ?",
                (cutoff,),
            ).fetchall()
            ids = [r[0] for r in rows]
            if not ids:
                return []

            placeholders = ",".join("?" for _ in ids)
            con.execute(
                f"""
                UPDATE approvals
                SET status = 'rejected', decision_ts = ?, decision_reason = ?
                WHERE id IN ({placeholders})
                """,
                (time.time(), reason, *ids),
            )
            return ids

    def mark_dispatched(self, approval_id: str, success: bool, result: dict[str, Any]) -> bool:
        # Keep the historical failure status value for compatibility with
        # existing approval lifecycle consumers.
        next_status = "processed" if success else "failed"
        with sqlite3.connect(self.db_path) as con:
            cur = con.execute(
                """
                UPDATE approvals
                SET status = ?, dispatch_ts = ?, dispatch_result = ?
                WHERE id = ? AND status = 'approved'
                """,
                (next_status, time.time(), json.dumps(result, sort_keys=True), approval_id),
            )
            return cur.rowcount == 1
