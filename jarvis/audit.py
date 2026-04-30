"""Append-only, hash-chained SQLite audit log.

Each row's hash includes the previous row's hash. Modifying any row in place
breaks the chain — `verify()` will return False and tell you something
tampered with the log (or something is buggy).

Cheap to maintain (one SHA-256 per insert), zero ops, gives you replayability
and tamper-evidence.
"""
import sqlite3
import json
import hashlib
import time
from io import TextIOBase
from pathlib import Path
from typing import Any, Optional


_REDACT_PATTERNS: frozenset[str] = frozenset(
    {
        "api_key",
        "password",
        "token",
        "secret",
        "card_number",
        "cvv",
        "ssn",
    }
)


def redact_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Return a deep-redacted copy of payload for sensitive-key fields."""

    def _is_sensitive(key: str) -> bool:
        key_norm = key.lower()
        return any(pattern in key_norm for pattern in _REDACT_PATTERNS)

    def _redact_value(value: Any) -> Any:
        if isinstance(value, dict):
            return {
                k: ("[REDACTED]" if _is_sensitive(k) else _redact_value(v))
                for k, v in value.items()
            }
        if isinstance(value, list):
            return [_redact_value(item) for item in value]
        return value

    return _redact_value(payload)


class AuditLog:
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as con:
            con.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts REAL NOT NULL,
                    kind TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    prev_hash TEXT NOT NULL,
                    hash TEXT NOT NULL
                )
            """)
            con.execute("CREATE INDEX IF NOT EXISTS events_kind_idx ON events(kind)")

    def _last_hash(self) -> str:
        with sqlite3.connect(self.db_path) as con:
            row = con.execute(
                "SELECT hash FROM events ORDER BY id DESC LIMIT 1"
            ).fetchone()
        return row[0] if row else "0" * 64

    def append(self, kind: str, payload: dict[str, Any]) -> int:
        """Append an event. Returns the new row id."""
        ts = time.time()
        prev = self._last_hash()
        body = json.dumps(redact_payload(payload), sort_keys=True, default=str)
        digest = hashlib.sha256(
            f"{prev}|{ts}|{kind}|{body}".encode()
        ).hexdigest()
        with sqlite3.connect(self.db_path) as con:
            cur = con.execute(
                "INSERT INTO events (ts, kind, payload, prev_hash, hash) "
                "VALUES (?, ?, ?, ?, ?)",
                (ts, kind, body, prev, digest),
            )
            return cur.lastrowid

    def verify(self) -> bool:
        """Walk the chain from row 1. True if every hash matches."""
        with sqlite3.connect(self.db_path) as con:
            rows = con.execute(
                "SELECT ts, kind, payload, prev_hash, hash "
                "FROM events ORDER BY id ASC"
            ).fetchall()
        prev = "0" * 64
        for ts, kind, payload, stored_prev, stored_hash in rows:
            if stored_prev != prev:
                return False
            digest = hashlib.sha256(
                f"{prev}|{ts}|{kind}|{payload}".encode()
            ).hexdigest()
            if digest != stored_hash:
                return False
            prev = digest
        return True

    def recent(
        self,
        limit: int = 50,
        kind: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """Most recent events first. Filter by `kind` if given."""
        with sqlite3.connect(self.db_path) as con:
            if kind:
                rows = con.execute(
                    "SELECT id, ts, kind, payload FROM events "
                    "WHERE kind = ? ORDER BY id DESC LIMIT ?",
                    (kind, limit),
                ).fetchall()
            else:
                rows = con.execute(
                    "SELECT id, ts, kind, payload FROM events "
                    "ORDER BY id DESC LIMIT ?",
                    (limit,),
                ).fetchall()
        return [
            {
                "id": r[0],
                "ts": r[1],
                "kind": r[2],
                "payload": json.loads(r[3]) if r[3] else {},
            }
            for r in rows
        ]

    def by_correlation_id(
        self,
        correlation_id: str,
        limit: int = 100,
        kind: str | None = None,
    ) -> list[dict[str, Any]]:
        """Most recent events first for a specific correlation_id.

        Since payload is stored as JSON text, this uses a fast LIKE pre-filter
        and then exact payload-key matching after JSON decode.
        """
        safe_limit = max(1, min(int(limit), 1000))
        needle = f'%"correlation_id": "{correlation_id}"%'

        with sqlite3.connect(self.db_path) as con:
            if kind:
                rows = con.execute(
                    "SELECT id, ts, kind, payload FROM events "
                    "WHERE kind = ? AND payload LIKE ? ORDER BY id DESC LIMIT ?",
                    (kind, needle, safe_limit),
                ).fetchall()
            else:
                rows = con.execute(
                    "SELECT id, ts, kind, payload FROM events "
                    "WHERE payload LIKE ? ORDER BY id DESC LIMIT ?",
                    (needle, safe_limit),
                ).fetchall()

        matched: list[dict[str, Any]] = []
        for row in rows:
            payload = json.loads(row[3])
            if payload.get("correlation_id") != correlation_id:
                continue
            if kind and row[2] != kind:
                continue
            matched.append(
                {
                    "id": row[0],
                    "ts": row[1],
                    "kind": row[2],
                    "payload": payload,
                }
            )
        return matched

    def export_jsonl(self, out: TextIOBase) -> int:
        """Stream all events as JSONL rows to `out`. Returns row count."""
        with sqlite3.connect(self.db_path) as con:
            rows = con.execute(
                "SELECT id, ts, kind, payload, prev_hash, hash "
                "FROM events ORDER BY id ASC"
            ).fetchall()

        count = 0
        for row in rows:
            record = {
                "id": row[0],
                "ts": row[1],
                "kind": row[2],
                "payload": json.loads(row[3]),
                "prev_hash": row[4],
                "hash": row[5],
            }
            out.write(json.dumps(record, sort_keys=True) + "\n")
            count += 1
        return count

    def tail(self, since_id: int = 0, limit: int = 50) -> list[dict[str, Any]]:
        """Return events with id > since_id, oldest first. Used for SSE streaming."""
        with sqlite3.connect(self.db_path) as con:
            rows = con.execute(
                "SELECT id, ts, kind, payload FROM events "
                "WHERE id > ? ORDER BY id ASC LIMIT ?",
                (since_id, limit),
            ).fetchall()
        return [
            {"id": r[0], "ts": r[1], "kind": r[2], "payload": json.loads(r[3])}
            for r in rows
        ]

    def stats(self) -> dict[str, Any]:
        """Return aggregate audit statistics."""
        with sqlite3.connect(self.db_path) as con:
            count_row = con.execute("SELECT COUNT(*) FROM events").fetchone()
            ts_row = con.execute(
                "SELECT MIN(ts), MAX(ts) FROM events"
            ).fetchone()
            kind_rows = con.execute(
                "SELECT kind, COUNT(*) FROM events GROUP BY kind ORDER BY kind ASC"
            ).fetchall()

        return {
            "kinds": {row[0]: row[1] for row in kind_rows},
            "oldest_ts": ts_row[0] if ts_row else None,
            "newest_ts": ts_row[1] if ts_row else None,
            "chain_length": count_row[0] if count_row else 0,
        }
