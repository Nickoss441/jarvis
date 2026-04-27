"""Tests for the internal payments budget ledger and rollover logic."""

from datetime import datetime, timedelta, timezone

from jarvis.payments_ledger import PaymentsBudgetLedger, month_key_for, previous_month_key


def test_month_key_and_previous_month_key() -> None:
    assert month_key_for(datetime(2026, 4, 26, tzinfo=timezone.utc)) == "2026-04"
    assert previous_month_key("2026-04") == "2026-03"
    assert previous_month_key("2026-01") == "2025-12"


def test_effective_cap_no_previous_month_activity_keeps_base_cap(tmp_path) -> None:
    ledger = PaymentsBudgetLedger(tmp_path / "budget.db")

    cap = ledger.effective_month_cap("2026-04", "USD", 100.0)

    assert cap == 100.0


def test_effective_cap_rolls_over_unused_previous_month_budget(tmp_path) -> None:
    ledger = PaymentsBudgetLedger(tmp_path / "budget.db")

    prev_ts = datetime(2026, 3, 20, tzinfo=timezone.utc)
    ledger.record_transaction(
        ts=prev_ts,
        currency="USD",
        amount=40.0,
        recipient="alice@example.com",
        reason="seed",
        mcc="5411",
        external_txid="tx-prev",
        monthly_cap=100.0,
    )

    cap = ledger.effective_month_cap("2026-04", "USD", 100.0)

    assert cap == 160.0


def test_record_transaction_updates_monthly_spend(tmp_path) -> None:
    ledger = PaymentsBudgetLedger(tmp_path / "budget.db")
    ts = datetime(2026, 4, 5, tzinfo=timezone.utc)

    ledger.record_transaction(
        ts=ts,
        currency="USD",
        amount=12.5,
        recipient="shop@example.com",
        reason="snacks",
        mcc="5812",
        external_txid="tx-1",
        monthly_cap=100.0,
    )
    ledger.record_transaction(
        ts=ts + timedelta(hours=1),
        currency="USD",
        amount=7.5,
        recipient="shop@example.com",
        reason="coffee",
        mcc="5814",
        external_txid="tx-2",
        monthly_cap=100.0,
    )

    spend = ledger.monthly_spend("2026-04", "USD")

    assert spend == 20.0


def test_record_reconciliation_event_and_detect_duplicate(tmp_path) -> None:
    ledger = PaymentsBudgetLedger(tmp_path / "budget.db")
    now = datetime.now(timezone.utc)

    inserted = ledger.record_reconciliation_event(
        ts=now,
        provider="stripe",
        event_id="evt_1",
        external_txid="ch_1",
        amount=12.0,
        currency="USD",
        merchant="Cafe",
        status="unexpected",
        matched_internal_txid="",
        raw_payload_json='{"id":"evt_1"}',
    )
    duplicate = ledger.record_reconciliation_event(
        ts=now,
        provider="stripe",
        event_id="evt_1",
        external_txid="ch_1",
        amount=12.0,
        currency="USD",
        merchant="Cafe",
        status="unexpected",
        matched_internal_txid="",
        raw_payload_json='{"id":"evt_1"}',
    )

    assert inserted is True
    assert duplicate is False
