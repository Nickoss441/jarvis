from datetime import datetime, timezone

import pytest

from jarvis.tools.debt_payoff_planner import (
    DebtAccount,
    DebtPayoffPlanner,
    DebtStatus,
    DebtType,
    PayoffPlan,
    PayoffProjection,
    PayoffStrategy,
    PaymentRecord,
)


def _utc(year: int, month: int, day: int) -> datetime:
    return datetime(year, month, day, tzinfo=timezone.utc)


def test_debt_account_validation_balance_negative():
    with pytest.raises(ValueError, match="principal_balance"):
        DebtAccount(
            debt_id="d1",
            name="Card",
            debt_type=DebtType.CREDIT_CARD,
            principal_balance=-1,
            interest_rate=19.99,
            minimum_payment=50,
            due_day=12,
            opened_at=_utc(2024, 1, 1),
        )


def test_debt_account_validation_interest_range():
    with pytest.raises(ValueError, match="interest_rate"):
        DebtAccount(
            debt_id="d1",
            name="Card",
            debt_type=DebtType.CREDIT_CARD,
            principal_balance=1000,
            interest_rate=150,
            minimum_payment=50,
            due_day=12,
            opened_at=_utc(2024, 1, 1),
        )


def test_debt_account_validation_opened_at_must_be_tz_aware():
    with pytest.raises(ValueError, match="timezone-aware"):
        DebtAccount(
            debt_id="d1",
            name="Card",
            debt_type=DebtType.CREDIT_CARD,
            principal_balance=1000,
            interest_rate=19.99,
            minimum_payment=50,
            due_day=12,
            opened_at=datetime(2024, 1, 1),
        )


def test_debt_account_monthly_rate_and_interest_estimate():
    debt = DebtAccount(
        debt_id="d1",
        name="Card",
        debt_type=DebtType.CREDIT_CARD,
        principal_balance=1200,
        interest_rate=24,
        minimum_payment=50,
        due_day=10,
        opened_at=_utc(2024, 1, 1),
    )
    assert debt.monthly_interest_rate == pytest.approx(0.02)
    assert debt.estimated_monthly_interest == pytest.approx(24)


def test_payment_record_validation_amount_negative():
    with pytest.raises(ValueError, match="amount"):
        PaymentRecord(
            payment_id="p1",
            debt_id="d1",
            amount=-1,
            paid_at=_utc(2024, 2, 1),
            principal_paid=0,
            interest_paid=0,
        )


def test_add_debt_account_marks_zero_balance_as_paid_off():
    planner = DebtPayoffPlanner()
    debt = planner.add_debt_account(
        name="Closed account",
        debt_type=DebtType.OTHER,
        principal_balance=0,
        interest_rate=0,
        minimum_payment=0,
        due_day=1,
        opened_at=_utc(2024, 1, 1),
    )
    assert debt.status == DebtStatus.PAID_OFF


def test_record_payment_unknown_debt_raises_key_error():
    planner = DebtPayoffPlanner()
    with pytest.raises(KeyError, match="debt not found"):
        planner.record_payment("missing", 100, _utc(2024, 2, 1))


def test_record_payment_applies_principal_and_marks_paid_off():
    planner = DebtPayoffPlanner()
    debt = planner.add_debt_account(
        name="Card",
        debt_type=DebtType.CREDIT_CARD,
        principal_balance=500,
        interest_rate=20,
        minimum_payment=25,
        due_day=10,
        opened_at=_utc(2024, 1, 1),
    )

    payment = planner.record_payment(
        debt_id=debt.debt_id,
        amount=500,
        paid_at=_utc(2024, 2, 1),
        principal_paid=500,
    )

    assert payment.principal_paid == pytest.approx(500)
    assert planner.debts[debt.debt_id].principal_balance == pytest.approx(0)
    assert planner.debts[debt.debt_id].status == DebtStatus.PAID_OFF


def test_record_payment_defaults_principal_from_amount_minus_interest():
    planner = DebtPayoffPlanner()
    debt = planner.add_debt_account(
        name="Card",
        debt_type=DebtType.CREDIT_CARD,
        principal_balance=300,
        interest_rate=20,
        minimum_payment=25,
        due_day=10,
        opened_at=_utc(2024, 1, 1),
    )

    payment = planner.record_payment(
        debt_id=debt.debt_id,
        amount=100,
        paid_at=_utc(2024, 2, 1),
        interest_paid=10,
    )

    assert payment.principal_paid == pytest.approx(90)
    assert planner.debts[debt.debt_id].principal_balance == pytest.approx(210)


def test_get_total_debt_balance_counts_only_active_debts():
    planner = DebtPayoffPlanner()
    planner.add_debt_account("A", DebtType.CREDIT_CARD, 100, 20, 10, 5, _utc(2024, 1, 1))
    planner.add_debt_account("B", DebtType.AUTO_LOAN, 200, 7, 20, 5, _utc(2024, 1, 1))
    planner.add_debt_account("C", DebtType.OTHER, 0, 0, 0, 5, _utc(2024, 1, 1))

    assert planner.get_total_debt_balance() == pytest.approx(300)


def test_monthly_minimum_obligation_sums_active_debts_only():
    planner = DebtPayoffPlanner()
    planner.add_debt_account("A", DebtType.CREDIT_CARD, 100, 20, 10, 5, _utc(2024, 1, 1))
    planner.add_debt_account("B", DebtType.AUTO_LOAN, 200, 7, 20, 5, _utc(2024, 1, 1))
    planner.add_debt_account("C", DebtType.OTHER, 0, 0, 999, 5, _utc(2024, 1, 1))

    assert planner.get_monthly_minimum_obligation() == pytest.approx(30)


def test_weighted_average_interest_rate():
    planner = DebtPayoffPlanner()
    planner.add_debt_account("A", DebtType.CREDIT_CARD, 1000, 20, 25, 1, _utc(2024, 1, 1))
    planner.add_debt_account("B", DebtType.AUTO_LOAN, 500, 8, 25, 1, _utc(2024, 1, 1))

    expected = (1000 * 20 + 500 * 8) / 1500
    assert planner.get_weighted_average_interest_rate() == pytest.approx(expected)


def test_weighted_average_interest_rate_returns_zero_without_active_debts():
    planner = DebtPayoffPlanner()
    assert planner.get_weighted_average_interest_rate() == 0.0


def test_suggest_payoff_order_snowball_smallest_balance_first():
    planner = DebtPayoffPlanner()
    a = planner.add_debt_account("A", DebtType.CREDIT_CARD, 1000, 20, 25, 1, _utc(2024, 1, 1))
    b = planner.add_debt_account("B", DebtType.AUTO_LOAN, 200, 8, 25, 1, _utc(2024, 1, 1))
    c = planner.add_debt_account("C", DebtType.PERSONAL_LOAN, 500, 14, 25, 1, _utc(2024, 1, 1))

    ordered = planner.suggest_payoff_order(PayoffStrategy.SNOWBALL)
    assert ordered == [b.debt_id, c.debt_id, a.debt_id]


def test_suggest_payoff_order_avalanche_highest_apr_first():
    planner = DebtPayoffPlanner()
    a = planner.add_debt_account("A", DebtType.CREDIT_CARD, 1000, 26, 25, 1, _utc(2024, 1, 1))
    b = planner.add_debt_account("B", DebtType.AUTO_LOAN, 200, 8, 25, 1, _utc(2024, 1, 1))
    c = planner.add_debt_account("C", DebtType.PERSONAL_LOAN, 500, 14, 25, 1, _utc(2024, 1, 1))

    ordered = planner.suggest_payoff_order(PayoffStrategy.AVALANCHE)
    assert ordered == [a.debt_id, c.debt_id, b.debt_id]


def test_suggest_payoff_order_custom_falls_back_to_avalanche():
    planner = DebtPayoffPlanner()
    a = planner.add_debt_account("A", DebtType.CREDIT_CARD, 1000, 26, 25, 1, _utc(2024, 1, 1))
    b = planner.add_debt_account("B", DebtType.AUTO_LOAN, 200, 8, 25, 1, _utc(2024, 1, 1))

    ordered = planner.suggest_payoff_order(PayoffStrategy.CUSTOM)
    assert ordered == [a.debt_id, b.debt_id]


def test_suggest_payoff_order_hybrid_prefers_rate_with_balance_weight():
    planner = DebtPayoffPlanner()
    high_apr = planner.add_debt_account(
        "High APR", DebtType.CREDIT_CARD, 300, 29, 25, 1, _utc(2024, 1, 1)
    )
    high_bal = planner.add_debt_account(
        "High Balance", DebtType.STUDENT_LOAN, 2000, 10, 25, 1, _utc(2024, 1, 1)
    )

    ordered = planner.suggest_payoff_order(PayoffStrategy.HYBRID)
    assert ordered[0] in {high_apr.debt_id, high_bal.debt_id}
    assert set(ordered) == {high_apr.debt_id, high_bal.debt_id}


def test_simulate_payoff_rejects_negative_budget_or_extra():
    planner = DebtPayoffPlanner()
    with pytest.raises(ValueError, match="non-negative"):
        planner.simulate_payoff(PayoffStrategy.SNOWBALL, -1)

    with pytest.raises(ValueError, match="non-negative"):
        planner.simulate_payoff(PayoffStrategy.SNOWBALL, 100, -1)


def test_simulate_payoff_rejects_budget_below_minimum_required():
    planner = DebtPayoffPlanner()
    planner.add_debt_account("A", DebtType.CREDIT_CARD, 1000, 20, 100, 1, _utc(2024, 1, 1))

    with pytest.raises(ValueError, match="below minimum"):
        planner.simulate_payoff(PayoffStrategy.SNOWBALL, 99)


def test_simulate_payoff_single_debt_completes():
    planner = DebtPayoffPlanner()
    planner.add_debt_account("A", DebtType.CREDIT_CARD, 1200, 0, 100, 1, _utc(2024, 1, 1))

    projection = planner.simulate_payoff(
        strategy=PayoffStrategy.SNOWBALL,
        monthly_budget=100,
        extra_payment=0,
    )

    assert projection.months_to_debt_free == 12
    assert projection.total_interest_paid == pytest.approx(0)
    assert projection.total_paid == pytest.approx(1200)
    assert projection.estimated_payoff_date is not None


def test_simulate_payoff_returns_none_date_if_not_resolved_within_max_months():
    planner = DebtPayoffPlanner()
    planner.add_debt_account("A", DebtType.CREDIT_CARD, 1000, 30, 25, 1, _utc(2024, 1, 1))

    projection = planner.simulate_payoff(
        strategy=PayoffStrategy.SNOWBALL,
        monthly_budget=25,
        max_months=1,
    )

    assert projection.months_to_debt_free == 1
    assert projection.estimated_payoff_date is None


def test_generate_payoff_plan_contains_projection_and_order():
    planner = DebtPayoffPlanner()
    a = planner.add_debt_account("A", DebtType.CREDIT_CARD, 600, 20, 50, 1, _utc(2024, 1, 1))
    b = planner.add_debt_account("B", DebtType.AUTO_LOAN, 300, 8, 25, 1, _utc(2024, 1, 1))

    plan = planner.generate_payoff_plan(
        strategy=PayoffStrategy.SNOWBALL,
        monthly_budget=150,
        extra_payment=25,
    )

    assert isinstance(plan, PayoffPlan)
    assert isinstance(plan.projection, PayoffProjection)
    assert plan.ordered_debt_ids[0] == b.debt_id
    assert set(plan.ordered_debt_ids) == {a.debt_id, b.debt_id}


def test_to_dict_methods_return_expected_shape():
    planner = DebtPayoffPlanner()
    debt = planner.add_debt_account(
        "Card", DebtType.CREDIT_CARD, 1000, 20, 50, 10, _utc(2024, 1, 1)
    )
    payment = planner.record_payment(
        debt_id=debt.debt_id,
        amount=100,
        paid_at=_utc(2024, 2, 1),
        interest_paid=20,
    )
    plan = planner.generate_payoff_plan(PayoffStrategy.AVALANCHE, monthly_budget=200)

    debt_dict = debt.to_dict()
    payment_dict = payment.to_dict()
    plan_dict = plan.to_dict()

    assert debt_dict["id"] == debt.debt_id
    assert payment_dict["debt_id"] == debt.debt_id
    assert plan_dict["strategy"] == PayoffStrategy.AVALANCHE.value
    assert "projection" in plan_dict


def test_get_active_debts_filters_paid_off():
    planner = DebtPayoffPlanner()
    debt = planner.add_debt_account(
        "Card", DebtType.CREDIT_CARD, 100, 20, 10, 5, _utc(2024, 1, 1)
    )
    planner.record_payment(debt.debt_id, 100, _utc(2024, 2, 1), principal_paid=100)

    assert planner.get_active_debts() == []


def test_record_payment_cannot_apply_more_principal_than_balance():
    planner = DebtPayoffPlanner()
    debt = planner.add_debt_account(
        "Card", DebtType.CREDIT_CARD, 80, 20, 10, 5, _utc(2024, 1, 1)
    )

    payment = planner.record_payment(
        debt.debt_id,
        amount=200,
        paid_at=_utc(2024, 2, 1),
        principal_paid=150,
    )

    assert payment.principal_paid == pytest.approx(80)
    assert planner.debts[debt.debt_id].principal_balance == pytest.approx(0)


def test_generate_payoff_plan_with_no_active_debts_returns_zero_projection():
    planner = DebtPayoffPlanner()
    plan = planner.generate_payoff_plan(
        strategy=PayoffStrategy.SNOWBALL,
        monthly_budget=100,
    )

    assert plan.ordered_debt_ids == []
    assert plan.projection.months_to_debt_free == 0
    assert plan.projection.total_interest_paid == pytest.approx(0)
    assert plan.projection.total_paid == pytest.approx(0)


def test_simulate_payoff_uses_extra_payment_to_reduce_months():
    planner = DebtPayoffPlanner()
    planner.add_debt_account(
        "Card", DebtType.CREDIT_CARD, 1000, 0, 100, 10, _utc(2024, 1, 1)
    )

    baseline = planner.simulate_payoff(PayoffStrategy.SNOWBALL, monthly_budget=100, extra_payment=0)
    accelerated = planner.simulate_payoff(PayoffStrategy.SNOWBALL, monthly_budget=100, extra_payment=100)

    assert accelerated.months_to_debt_free < baseline.months_to_debt_free
