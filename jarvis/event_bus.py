"""Event bus for perception layer.

Simple publish/subscribe event system backed by SQLite. Monitors emit events,
subscribers poll/receive them. Events are append-only and audit-logged.
"""
import json
import sqlite3
import time
from pathlib import Path
from typing import Optional

from .runtime import RuntimeEventEnvelope


Event = RuntimeEventEnvelope


class EventBus:
    """SQLite-backed event bus for perception monitors.

    Monitors emit events; subscribers poll the queue or register callbacks.
    Events are immutable and audit-logged.
    """

    def __init__(self, db_path: Path | str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        """Create events table if not exists."""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id TEXT PRIMARY KEY,
                    kind TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    source TEXT NOT NULL,
                    correlation_id TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    processed INTEGER NOT NULL DEFAULT 0,
                    processed_at REAL,
                    notes TEXT,
                    created_at REAL NOT NULL
                )
            """)
            cols = {
                row[1]
                for row in conn.execute("PRAGMA table_info(events)").fetchall()
            }
            if "correlation_id" not in cols:
                conn.execute(
                    "ALTER TABLE events ADD COLUMN correlation_id TEXT NOT NULL DEFAULT ''"
                )
                conn.execute(
                    "UPDATE events SET correlation_id = id WHERE correlation_id = ''"
                )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_kind ON events (kind)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_source ON events (source)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_correlation_id ON events (correlation_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_processed ON events (processed)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_timestamp ON events (timestamp DESC)"
            )
            conn.commit()
        finally:
            conn.close()

    def emit(self, event: Event) -> str:
        """Emit an event onto the bus.

        Args:
            event: Event instance

        Returns:
            event.id
        """
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                """
                INSERT INTO events (
                    id, kind, timestamp, source, correlation_id, payload, processed, notes, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.id,
                    event.kind,
                    event.timestamp,
                    event.source,
                    event.correlation_id,
                    json.dumps(event.payload),
                    int(event.processed),
                    event.notes,
                    time.time(),
                ),
            )
            conn.commit()
        finally:
            conn.close()
        return event.id

    def list_unprocessed(self, limit: int = 100, kind: Optional[str] = None) -> list[Event]:
        """List unprocessed events, optionally filtered by kind.

        Args:
            limit: Max events to return
            kind: Optional kind filter

        Returns:
            List of Event objects
        """
        conn = sqlite3.connect(self.db_path)
        try:
            if kind:
                rows = conn.execute(
                    """
                    SELECT id, kind, timestamp, source, correlation_id, payload, processed, processed_at, notes
                    FROM events
                    WHERE processed = 0 AND kind = ?
                    ORDER BY timestamp ASC
                    LIMIT ?
                    """,
                    (kind, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT id, kind, timestamp, source, correlation_id, payload, processed, processed_at, notes
                    FROM events
                    WHERE processed = 0
                    ORDER BY timestamp ASC
                    LIMIT ?
                    """,
                    (limit,),
                ).fetchall()
            return [self._event_from_row(row) for row in rows]
        finally:
            conn.close()

    def mark_processed(self, event_id: str, notes: str = "") -> bool:
        """Mark an event as processed.

        Args:
            event_id: Event ID
            notes: Optional processing notes

        Returns:
            True if marked, False if not found
        """
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.execute(
                """
                UPDATE events
                SET processed = 1, processed_at = ?, notes = ?
                WHERE id = ?
                """,
                (time.time(), notes, event_id),
            )
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def get(self, event_id: str) -> Optional[Event]:
        """Retrieve an event by ID."""
        conn = sqlite3.connect(self.db_path)
        try:
            row = conn.execute(
                """
                SELECT id, kind, timestamp, source, correlation_id, payload, processed, processed_at, notes
                FROM events
                WHERE id = ?
                """,
                (event_id,),
            ).fetchone()
            if not row:
                return None
            return self._event_from_row(row)
        finally:
            conn.close()

    def recent(self, limit: int = 100, kind: Optional[str] = None) -> list[Event]:
        """List recent events, optionally filtered by kind.

        Args:
            limit: Max events to return
            kind: Optional kind filter

        Returns:
            List of Event objects, newest first
        """
        conn = sqlite3.connect(self.db_path)
        try:
            if kind:
                rows = conn.execute(
                    """
                    SELECT id, kind, timestamp, source, correlation_id, payload, processed, processed_at, notes
                    FROM events
                    WHERE kind = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                    """,
                    (kind, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT id, kind, timestamp, source, correlation_id, payload, processed, processed_at, notes
                    FROM events
                    ORDER BY timestamp DESC
                    LIMIT ?
                    """,
                    (limit,),
                ).fetchall()
            return [self._event_from_row(row) for row in rows]
        finally:
            conn.close()

    @staticmethod
    def _event_from_row(row: tuple) -> Event:
        payload = json.loads(row[5])
        return Event(
            id=row[0],
            kind=row[1],
            timestamp=row[2],
            source=row[3],
            correlation_id=row[4],
            payload=payload,
            processed=bool(row[6]),
            processed_at=row[7],
            notes=row[8],
        )

    def count(self, processed: Optional[bool] = None, kind: Optional[str] = None) -> int:
        """Count events, optionally filtered.

        Args:
            processed: If True, count processed only; if False, unprocessed only; if None, count all
            kind: Optional kind filter

        Returns:
            Event count
        """
        conn = sqlite3.connect(self.db_path)
        try:
            if processed is None:
                if kind:
                    return conn.execute(
                        "SELECT COUNT(*) FROM events WHERE kind = ?", (kind,)
                    ).fetchone()[0]
                return conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
            else:
                if kind:
                    return conn.execute(
                        "SELECT COUNT(*) FROM events WHERE processed = ? AND kind = ?",
                        (int(processed), kind),
                    ).fetchone()[0]
                return conn.execute(
                    "SELECT COUNT(*) FROM events WHERE processed = ?",
                    (int(processed),),
                ).fetchone()[0]
        finally:
            conn.close()

    def healthcheck(self) -> bool:
        """Check if the event bus database is healthy and accessible.

        Verifies:
        - Database file exists and is readable
        - Database is writable
        - Can perform basic read/write operations

        Returns:
            True if healthy, False otherwise
        """
        try:
            if not self.db_path.exists():
                return False

            conn = sqlite3.connect(self.db_path, timeout=5.0)
            try:
                conn.execute("SELECT 1 FROM events LIMIT 1").fetchone()
                conn.execute("BEGIN IMMEDIATE")
                conn.execute(
                    "CREATE TEMP TABLE IF NOT EXISTS healthcheck_tmp (id INTEGER PRIMARY KEY)"
                )
                conn.execute("INSERT INTO healthcheck_tmp DEFAULT VALUES")
                conn.rollback()
                return True
            except sqlite3.Error:
                return False
            finally:
                conn.close()
        except Exception:
            return False
