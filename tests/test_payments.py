"""Tests for payments tool and dispatcher."""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from jarvis.tools.payments import (
    build_payment_proposal,
    dispatch_payment,
    make_payments_tool,
    spend_tier_for_amount,
)


def test_dispatch_payment_dry_run(tmp_path):
    """Test dry-run payment logging."""
    ledger = tmp_path / "payments.jsonl"
    result = dispatch_payment(
        mode="dry_run",
        ledger_path=ledger,
        payload={
            "amount": 100.50,
            "currency": "USD",
            "recipient": "alice@example.com",
            "reason": "Invoice payment",
        },
    )

    assert result["status"] == "dry_run_logged"
    assert result["amount"] == 100.50
    assert result["currency"] == "USD"
    assert ledger.exists()

    # Verify log entry
    logged = json.loads(ledger.read_text())
    assert logged["amount"] == 100.50
    assert logged["currency"] == "USD"
    assert logged["recipient"] == "alice@example.com"
    assert logged["mode"] == "dry_run"


def test_dispatch_payment_missing_amount(tmp_path):
    """Test that missing amount returns error."""
    ledger = tmp_path / "payments.jsonl"
    result = dispatch_payment(
        mode="dry_run",
        ledger_path=ledger,
        payload={
            "currency": "USD",
            "recipient": "bob@example.com",
        },
    )

    assert "error" in result
    assert "amount" in result["error"]


def test_dispatch_payment_budget_cap(tmp_path):
    """Test that amounts exceeding budget cap are rejected."""
    ledger = tmp_path / "payments.jsonl"
    result = dispatch_payment(
        mode="dry_run",
        ledger_path=ledger,
        payload={
            "amount": 50000,
            "currency": "USD",
            "recipient": "charlie@example.com",
        },
    )

    assert "error" in result
    assert "tx_limit" in result["error"]


def test_dispatch_payment_invalid_currency(tmp_path):
    """Test that invalid currency format is rejected."""
    ledger = tmp_path / "payments.jsonl"
    result = dispatch_payment(
        mode="dry_run",
        ledger_path=ledger,
        payload={
            "amount": 100,
            "currency": "USDA",  # Wrong format
            "recipient": "dave@example.com",
        },
    )

    assert "error" in result
    assert "currency" in result["error"]


def test_make_payments_tool_with_approval():
    """Test payments tool factory with approval gating."""
    approval_store = {}

    def mock_request_approval(kind, payload):
        aid = "approval-456"
        approval_store[aid] = {
            "id": aid,
            "kind": kind,
            "payload": payload,
            "correlation_id": "corr-789",
        }
        return aid

    def mock_get_approval(aid):
        return approval_store.get(aid)

    tool = make_payments_tool(
        request_approval=mock_request_approval,
        get_approval=mock_get_approval,
    )

    assert tool.name == "payments"
    assert tool.tier == "gated"

    result = tool.handler(
        amount=250.00,
        currency="EUR",
        recipient="eve@example.com",
        reason="Contractor payment",
    )

    assert result["status"] == "pending_approval"
    assert result["kind"] == "payments"
    assert result["amount"] == 250.00
    assert result["currency"] == "EUR"
    assert result["correlation_id"] == "corr-789"


def test_make_payments_tool_negative_amount():
    """Test that negative amount is rejected at tool level."""
    def mock_request_approval(kind, payload):
        return "aid-123"

    tool = make_payments_tool(
        request_approval=mock_request_approval,
    )

    result = tool.handler(
        amount=-50.00,
        currency="USD",
        recipient="frank@example.com",
    )

    assert "error" in result


def test_dispatch_payment_tx_limit_override(tmp_path):
    ledger = tmp_path / "payments.jsonl"
    result = dispatch_payment(
        mode="dry_run",
        ledger_path=ledger,
        payload={
            "amount": 300,
            "currency": "USD",
            "recipient": "limit@example.com",
        },
        tx_limit=250,
    )

    assert "error" in result
    assert "tx_limit" in result["error"]


def test_dispatch_payment_monthly_cap_exceeded(tmp_path):
    ledger = tmp_path / "payments.jsonl"
    budget_db = tmp_path / "payments-budget.db"

    seed = dispatch_payment(
        mode="dry_run",
        ledger_path=ledger,
        payload={
            "amount": 90.0,
            "currency": "USD",
            "recipient": "existing@example.com",
        },
        monthly_cap=100.0,
        budget_db_path=budget_db,
    )
    assert seed["status"] == "dry_run_logged"

    result = dispatch_payment(
        mode="dry_run",
        ledger_path=ledger,
        payload={
            "amount": 20.0,
            "currency": "USD",
            "recipient": "new@example.com",
        },
        monthly_cap=100.0,
        budget_db_path=budget_db,
    )

    assert "error" in result
    assert "monthly cap exceeded" in result["error"]


def test_dispatch_payment_monthly_cap_ignores_previous_month(tmp_path):
    ledger = tmp_path / "payments.jsonl"
    previous_month = datetime.now(timezone.utc) - timedelta(days=40)
    existing = {
        "ts": previous_month.isoformat(),
        "txid": "old",
        "amount": 99.0,
        "currency": "USD",
        "recipient": "old@example.com",
        "reason": "old",
        "mode": "dry_run",
    }
    ledger.write_text(json.dumps(existing) + "\n", encoding="utf-8")

    result = dispatch_payment(
        mode="dry_run",
        ledger_path=ledger,
        payload={
            "amount": 20.0,
            "currency": "USD",
            "recipient": "new@example.com",
        },
        monthly_cap=50.0,
    )

    assert result["status"] == "dry_run_logged"


def test_dispatch_payment_requires_mcc_when_allowlist_configured(tmp_path):
    ledger = tmp_path / "payments.jsonl"
    result = dispatch_payment(
        mode="dry_run",
        ledger_path=ledger,
        payload={
            "amount": 10,
            "currency": "USD",
            "recipient": "mcc@example.com",
        },
        allowed_mccs=("5812",),
    )

    assert "error" in result
    assert "mcc is required" in result["error"]


def test_dispatch_payment_rejects_disallowed_mcc(tmp_path):
    ledger = tmp_path / "payments.jsonl"
    result = dispatch_payment(
        mode="dry_run",
        ledger_path=ledger,
        payload={
            "amount": 10,
            "currency": "USD",
            "recipient": "mcc@example.com",
            "mcc": "5999",
        },
        allowed_mccs=("5812", "5411"),
    )

    assert "error" in result
    assert "not allowed" in result["error"]


def test_dispatch_payment_accepts_allowed_mcc(tmp_path):
    ledger = tmp_path / "payments.jsonl"
    result = dispatch_payment(
        mode="dry_run",
        ledger_path=ledger,
        payload={
            "amount": 10,
            "currency": "USD",
            "recipient": "mcc@example.com",
            "mcc": "5812",
        },
        allowed_mccs=("5812", "5411"),
    )

    assert result["status"] == "dry_run_logged"


def test_make_payments_tool_includes_mcc_in_approval_payload():
    approval_store = {}

    def mock_request_approval(kind, payload):
        aid = "approval-mcc"
        approval_store[aid] = {
            "id": aid,
            "kind": kind,
            "payload": payload,
            "correlation_id": "corr-mcc",
        }
        return aid

    def mock_get_approval(aid):
        return approval_store.get(aid)

    tool = make_payments_tool(
        request_approval=mock_request_approval,
        get_approval=mock_get_approval,
    )

    result = tool.handler(
        amount=42.0,
        currency="USD",
        recipient="shop@example.com",
        reason="groceries",
        mcc="5411",
    )

    assert result["status"] == "pending_approval"
    assert approval_store["approval-mcc"]["payload"]["mcc"] == "5411"


def test_build_payment_proposal_valid_line_items() -> None:
    proposal = build_payment_proposal(
        amount=12.5,
        currency="usd",
        recipient="store@example.com",
        reason="lunch",
        merchant="Cafe Luna",
        line_items=[
            {"description": "Sandwich", "quantity": 1, "unit_price": 8.0},
            {"description": "Coffee", "quantity": 1, "unit_price": 4.5},
        ],
    )

    assert "error" not in proposal
    assert proposal["currency"] == "USD"
    assert proposal["merchant"] == "Cafe Luna"
    assert proposal["proposal_total"] == 12.5
    assert len(proposal["line_items"]) == 2


def test_build_payment_proposal_requires_merchant_with_line_items() -> None:
    proposal = build_payment_proposal(
        amount=8.0,
        currency="USD",
        recipient="store@example.com",
        line_items=[
            {"description": "Tea", "quantity": 1, "unit_price": 8.0},
        ],
    )

    assert "error" in proposal
    assert "merchant is required" in proposal["error"]


def test_build_payment_proposal_rejects_invalid_line_item() -> None:
    proposal = build_payment_proposal(
        amount=8.0,
        currency="USD",
        recipient="store@example.com",
        merchant="Cafe",
        line_items=[
            {"description": "Tea", "quantity": 0, "unit_price": 8.0},
        ],
    )

    assert "error" in proposal
    assert "quantity must be positive" in proposal["error"]


def test_build_payment_proposal_rejects_mismatched_line_item_total() -> None:
    proposal = build_payment_proposal(
        amount=10.0,
        currency="USD",
        recipient="store@example.com",
        merchant="Cafe",
        line_items=[
            {"description": "Tea", "quantity": 1, "unit_price": 8.0},
        ],
    )

    assert "error" in proposal
    assert "does not match line_items total" in proposal["error"]


def test_make_payments_tool_includes_merchant_and_line_items_payload() -> None:
    approval_store = {}

    def mock_request_approval(kind, payload):
        aid = "approval-proposal"
        approval_store[aid] = {
            "id": aid,
            "kind": kind,
            "payload": payload,
            "correlation_id": "corr-proposal",
        }
        return aid

    def mock_get_approval(aid):
        return approval_store.get(aid)

    tool = make_payments_tool(
        request_approval=mock_request_approval,
        get_approval=mock_get_approval,
    )

    result = tool.handler(
        amount=8.5,
        currency="USD",
        recipient="store@example.com",
        merchant="Cafe Luna",
        line_items=[
            {"description": "Coffee", "quantity": 1, "unit_price": 3.5},
            {"description": "Bagel", "quantity": 1, "unit_price": 5.0},
        ],
    )

    assert result["status"] == "pending_approval"
    payload = approval_store["approval-proposal"]["payload"]
    assert payload["merchant"] == "Cafe Luna"
    assert payload["proposal_total"] == 8.5
    assert len(payload["line_items"]) == 2


def test_spend_tier_boundaries() -> None:
    assert spend_tier_for_amount(0.01) == "0-10"
    assert spend_tier_for_amount(10.0) == "0-10"
    assert spend_tier_for_amount(10.01) == "10-100"
    assert spend_tier_for_amount(100.0) == "10-100"
    assert spend_tier_for_amount(100.01) == "100+"


def test_make_payments_tool_applies_spend_tier_and_risk_low() -> None:
    capture = {}

    def mock_request_approval(kind, payload, envelope=None):
        capture["kind"] = kind
        capture["payload"] = payload
        capture["envelope"] = envelope
        return "approval-tier-low"

    tool = make_payments_tool(request_approval=mock_request_approval)
    result = tool.handler(
        amount=9.99,
        currency="USD",
        recipient="merchant@example.com",
    )

    assert result["status"] == "pending_approval"
    assert result["spend_tier"] == "0-10"
    assert capture["payload"]["spend_tier"] == "0-10"
    assert capture["envelope"] is not None
    assert capture["envelope"].risk_tier == "low"


def test_make_payments_tool_applies_spend_tier_and_risk_medium() -> None:
    capture = {}

    def mock_request_approval(kind, payload, envelope=None):
        capture["payload"] = payload
        capture["envelope"] = envelope
        return "approval-tier-medium"

    tool = make_payments_tool(request_approval=mock_request_approval)
    result = tool.handler(
        amount=55.0,
        currency="USD",
        recipient="merchant@example.com",
    )

    assert result["spend_tier"] == "10-100"
    assert capture["payload"]["spend_tier"] == "10-100"
    assert capture["envelope"].risk_tier == "medium"


def test_make_payments_tool_applies_spend_tier_and_risk_high() -> None:
    capture = {}

    def mock_request_approval(kind, payload, envelope=None):
        capture["payload"] = payload
        capture["envelope"] = envelope
        return "approval-tier-high"

    tool = make_payments_tool(request_approval=mock_request_approval)
    result = tool.handler(
        amount=250.0,
        currency="USD",
        recipient="merchant@example.com",
    )

    assert result["spend_tier"] == "100+"
    assert capture["payload"]["spend_tier"] == "100+"
    assert capture["envelope"].risk_tier == "high"
