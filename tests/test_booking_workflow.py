from jarvis.booking_workflow import build_booking_decision


def test_booking_decision_rejects_non_positive_party_size() -> None:
    out = build_booking_decision(party_size=0, available=True)

    assert out["ok"] is False
    assert "party_size" in out["error"]


def test_booking_decision_defers_when_not_available() -> None:
    out = build_booking_decision(party_size=2, available=False, hold_minutes=15)

    assert out["ok"] is True
    assert out["action"] == "defer"
    assert out["requires_approval"] is False
    assert out["next_step"] == "offer_alternative_times"


def test_booking_decision_confirms_without_payment_when_no_deposit() -> None:
    out = build_booking_decision(
        party_size=2,
        available=True,
        deposit_per_person_eur=0,
    )

    assert out["action"] == "confirm_without_payment"
    assert out["deposit_total_eur"] == 0.0
    assert out["requires_approval"] is False


def test_booking_decision_requires_budget_override_when_user_max_exceeded() -> None:
    out = build_booking_decision(
        party_size=2,
        available=True,
        deposit_per_person_eur=30,
        user_max_deposit_eur=40,
        budget_remaining_eur=100,
    )

    assert out["action"] == "ask_user_budget_override"
    assert out["requires_approval"] is True
    assert out["deposit_total_eur"] == 60.0


def test_booking_decision_declines_when_budget_remaining_is_too_low() -> None:
    out = build_booking_decision(
        party_size=2,
        available=True,
        deposit_per_person_eur=25,
        budget_remaining_eur=40,
    )

    assert out["action"] == "decline_due_to_budget"
    assert out["next_step"] == "decline_and_offer_alternative"


def test_booking_decision_requests_manual_split_when_tx_limit_exceeded() -> None:
    out = build_booking_decision(
        party_size=3,
        available=True,
        deposit_per_person_eur=20,
        budget_remaining_eur=100,
        per_transaction_limit_eur=50,
    )

    assert out["action"] == "manual_split_payment"
    assert out["requires_approval"] is True


def test_booking_decision_requests_payment_approval_when_within_limits() -> None:
    out = build_booking_decision(
        party_size=2,
        available=True,
        deposit_per_person_eur=15,
        budget_remaining_eur=100,
        per_transaction_limit_eur=50,
        user_max_deposit_eur=40,
    )

    assert out["action"] == "request_payment_approval"
    assert out["requires_approval"] is True
    assert out["next_step"] == "create_deposit_approval"
    assert out["deposit_total_eur"] == 30.0
