"""Internal payments budget ledger with monthly rollover support."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def month_key_for(ts: datetime) -> str:
    return f"{ts.year:04d}-{ts.month:02d}"


def previous_month_key(month_key: str) -> str:
    year_s, month_s = month_key.split("-", 1)
    year = int(year_s)
    month = int(month_s)
    if month == 1:
        return f"{year - 1:04d}-12"
    return f"{year:04d}-{month - 1:02d}"


class PaymentsBudgetLedger:
    """SQLite-backed budget ledger used for monthly spend and rollover state."""

    def __init__(self, db_path: Path | str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _init_schema(self) -> None:
        with self._connect() as con:
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS payment_transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TEXT NOT NULL,
                    month_key TEXT NOT NULL,
                    currency TEXT NOT NULL,
                    amount REAL NOT NULL,
                    recipient TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    mcc TEXT NOT NULL,
                    external_txid TEXT NOT NULL
                )
                """
            )
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS payment_month_rollovers (
                    month_key TEXT NOT NULL,
                    currency TEXT NOT NULL,
                    carried_over REAL NOT NULL,
                    source_month_key TEXT NOT NULL,
                    created_ts TEXT NOT NULL,
                    PRIMARY KEY (month_key, currency)
                )
                """
            )
            con.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_payment_transactions_month_currency
                ON payment_transactions (month_key, currency)
                """
            )
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS payment_reconciliation_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    event_id TEXT NOT NULL,
                    external_txid TEXT NOT NULL,
                    amount REAL NOT NULL,
                    currency TEXT NOT NULL,
                    merchant TEXT NOT NULL,
                    status TEXT NOT NULL,
                    matched_internal_txid TEXT NOT NULL,
                    raw_payload_json TEXT NOT NULL,
                    UNIQUE(provider, event_id)
                )
                """
            )

    def monthly_spend(self, month_key: str, currency: str) -> float:
        with self._connect() as con:
            row = con.execute(
                """
                SELECT COALESCE(SUM(amount), 0)
                FROM payment_transactions
                WHERE month_key = ? AND currency = ?
                """,
                (month_key, currency.upper()),
            ).fetchone()
        return float(row[0] if row else 0.0)

    def monthly_transaction_count(self, month_key: str, currency: str) -> int:
        with self._connect() as con:
            row = con.execute(
                """
                SELECT COUNT(*)
                FROM payment_transactions
                WHERE month_key = ? AND currency = ?
                """,
                (month_key, currency.upper()),
            ).fetchone()
        return int(row[0] if row else 0)

    def _get_rollover(self, month_key: str, currency: str) -> float | None:
        with self._connect() as con:
            row = con.execute(
                """
                SELECT carried_over
                FROM payment_month_rollovers
                WHERE month_key = ? AND currency = ?
                """,
                (month_key, currency.upper()),
            ).fetchone()
        if row is None:
            return None
        return float(row[0])

    def ensure_month_rollover(self, month_key: str, currency: str, monthly_cap: float) -> float:
        existing = self._get_rollover(month_key, currency)
        if existing is not None:
            return existing

        prev_month = previous_month_key(month_key)
        prev_count = self.monthly_transaction_count(prev_month, currency)
        prev_spend = self.monthly_spend(prev_month, currency)
        carried = max(float(monthly_cap) - prev_spend, 0.0) if prev_count > 0 else 0.0

        with self._connect() as con:
            con.execute(
                """
                INSERT OR IGNORE INTO payment_month_rollovers (
                    month_key,
                    currency,
                    carried_over,
                    source_month_key,
                    created_ts
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    month_key,
                    currency.upper(),
                    carried,
                    prev_month,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )

        # Return what was persisted.
        return float(self._get_rollover(month_key, currency) or 0.0)

    def effective_month_cap(self, month_key: str, currency: str, monthly_cap: float) -> float:
        carried = self.ensure_month_rollover(month_key, currency, monthly_cap)
        return float(monthly_cap) + float(carried)

    def record_transaction(
        self,
        *,
        ts: datetime,
        currency: str,
        amount: float,
        recipient: str,
        reason: str,
        mcc: str,
        external_txid: str,
        monthly_cap: float,
    ) -> None:
        month_key = month_key_for(ts)
        normalized_currency = currency.upper()
        self.ensure_month_rollover(month_key, normalized_currency, monthly_cap)

        with self._connect() as con:
            con.execute(
                """
                INSERT INTO payment_transactions (
                    ts,
                    month_key,
                    currency,
                    amount,
                    recipient,
                    reason,
                    mcc,
                    external_txid
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    ts.isoformat(),
                    month_key,
                    normalized_currency,
                    float(amount),
                    recipient,
                    reason,
                    mcc,
                    external_txid,
                ),
            )

    def find_internal_txid_by_external_txid(self, external_txid: str) -> str | None:
        with self._connect() as con:
            row = con.execute(
                """
                SELECT external_txid
                FROM payment_transactions
                WHERE external_txid = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (external_txid,),
            ).fetchone()
        if row is None:
            return None
        return str(row[0])

    def record_reconciliation_event(
        self,
        *,
        ts: datetime,
        provider: str,
        event_id: str,
        external_txid: str,
        amount: float,
        currency: str,
        merchant: str,
        status: str,
        matched_internal_txid: str,
        raw_payload_json: str,
    ) -> bool:
        """Persist a reconciliation event.

        Returns False when the event is a duplicate (same provider+event_id).
        """
        with self._connect() as con:
            try:
                con.execute(
                    """
                    INSERT INTO payment_reconciliation_events (
                        ts,
                        provider,
                        event_id,
                        external_txid,
                        amount,
                        currency,
                        merchant,
                        status,
                        matched_internal_txid,
                        raw_payload_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        ts.isoformat(),
                        provider,
                        event_id,
                        external_txid,
                        float(amount),
                        currency.upper(),
                        merchant,
                        status,
                        matched_internal_txid,
                        raw_payload_json,
                    ),
                )
            except sqlite3.IntegrityError:
                return False
        return True
