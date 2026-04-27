from datetime import datetime, timezone

import pytest

from jarvis.tools.emergency_fund_planner import (
    CoverageSnapshot,
    EmergencyExpense,
    EmergencyFundAccount,
    EmergencyFundPlanner,
    ExpenseType,
    FundHealth,
    ReplenishmentPlan,
    WithdrawalRecord,
)


def _utc(year: int, month: int, day: int) -> datetime:
    return datetime(year, month, day, tzinfo=timezone.utc)


def test_emergency_expense_validation_negative_amount():
    with pytest.raises(ValueError, match="monthly_amount"):
        EmergencyExpense(
            expense_id="e1",
            name="Rent",
            expense_type=ExpenseType.HOUSING,
            monthly_amount=-1,
            essential=True,
            created_at=_utc(2024, 1, 1),
        )


def test_emergency_expense_validation_timezone_required():
    with pytest.raises(ValueError, match="timezone-aware"):
        EmergencyExpense(
            expense_id="e1",
            name="Rent",
            expense_type=ExpenseType.HOUSING,
            monthly_amount=1000,
            essential=True,
            created_at=datetime(2024, 1, 1),
        )


def test_fund_account_validation_negative_balance():
    with pytest.raises(ValueError, match="current_balance"):
        EmergencyFundAccount(
            account_id="a1",
            name="HYSA",
            current_balance=-10,
            annual_yield_pct=4,
            created_at=_utc(2024, 1, 1),
        )


def test_fund_account_validation_invalid_yield():
    with pytest.raises(ValueError, match="annual_yield_pct"):
        EmergencyFundAccount(
            account_id="a1",
            name="HYSA",
            current_balance=1000,
            annual_yield_pct=float("inf"),
            created_at=_utc(2024, 1, 1),
        )


def test_fund_account_monthly_yield_rate():
    account = EmergencyFundAccount(
        account_id="a1",
        name="HYSA",
        current_balance=1000,
        annual_yield_pct=4.8,
        created_at=_utc(2024, 1, 1),
    )
    assert account.monthly_yield_rate == pytest.approx(0.004)


def test_set_fund_account_registers_active_account():
    planner = EmergencyFundPlanner()
    account = planner.set_fund_account("HYSA", 5000, 4, _utc(2024, 1, 1))

    assert planner.fund_account is account
    assert account.name == "HYSA"


def test_add_expense_registers_expense():
    planner = EmergencyFundPlanner()
    expense = planner.add_expense(
        "Rent",
        ExpenseType.HOUSING,
        1800,
        True,
        _utc(2024, 1, 1),
    )

    assert expense.expense_id in planner.expenses
    assert planner.expenses[expense.expense_id].name == "Rent"


def test_total_monthly_expenses_essential_only_by_default():
    planner = EmergencyFundPlanner()
    planner.add_expense("Rent", ExpenseType.HOUSING, 1800, True, _utc(2024, 1, 1))
    planner.add_expense("Streaming", ExpenseType.OTHER, 20, False, _utc(2024, 1, 1))

    assert planner.get_total_monthly_expenses() == pytest.approx(1800)
    assert planner.get_total_monthly_expenses(include_nonessential=True) == pytest.approx(1820)


def test_calculate_target_amount_with_buffer():
    planner = EmergencyFundPlanner()
    planner.add_expense("Rent", ExpenseType.HOUSING, 1000, True, _utc(2024, 1, 1))
    planner.add_expense("Food", ExpenseType.FOOD, 500, True, _utc(2024, 1, 1))

    target = planner.calculate_target_amount(target_months=6, buffer_pct=10)
    assert target == pytest.approx(9900)


def test_calculate_target_amount_rejects_invalid_inputs():
    planner = EmergencyFundPlanner()

    with pytest.raises(ValueError, match="target_months"):
        planner.calculate_target_amount(target_months=-1)

    with pytest.raises(ValueError, match="buffer_pct"):
        planner.calculate_target_amount(buffer_pct=-5)


def test_coverage_snapshot_without_account_uses_zero_balance():
    planner = EmergencyFundPlanner()
    planner.add_expense("Rent", ExpenseType.HOUSING, 1000, True, _utc(2024, 1, 1))

    snapshot = planner.get_coverage_snapshot(target_months=6)

    assert isinstance(snapshot, CoverageSnapshot)
    assert snapshot.current_balance == pytest.approx(0)
    assert snapshot.months_covered == pytest.approx(0)
    assert snapshot.health == FundHealth.CRITICAL


def test_coverage_snapshot_health_underfunded():
    planner = EmergencyFundPlanner()
    planner.set_fund_account("HYSA", 3000, 4, _utc(2024, 1, 1))
    planner.add_expense("Rent", ExpenseType.HOUSING, 1500, True, _utc(2024, 1, 1))

    snapshot = planner.get_coverage_snapshot(target_months=6)
    assert snapshot.months_covered == pytest.approx(2)
    assert snapshot.health == FundHealth.UNDERFUNDED


def test_coverage_snapshot_health_adequate_and_strong():
    planner = EmergencyFundPlanner()
    planner.add_expense("Burn", ExpenseType.OTHER, 1000, True, _utc(2024, 1, 1))

    planner.set_fund_account("HYSA", 7000, 4, _utc(2024, 1, 1))
    adequate = planner.get_coverage_snapshot(target_months=6)
    assert adequate.health == FundHealth.ADEQUATE

    planner.set_fund_account("HYSA", 10000, 4, _utc(2024, 1, 1))
    strong = planner.get_coverage_snapshot(target_months=6)
    assert strong.health == FundHealth.STRONG


def test_coverage_snapshot_zero_burn_has_zero_months_covered():
    planner = EmergencyFundPlanner()
    planner.set_fund_account("HYSA", 5000, 4, _utc(2024, 1, 1))

    snapshot = planner.get_coverage_snapshot(target_months=6)
    assert snapshot.monthly_burn == pytest.approx(0)
    assert snapshot.months_covered == pytest.approx(0)


def test_estimate_required_monthly_contribution_zero_months_to_goal_uses_gap():
    planner = EmergencyFundPlanner()
    planner.set_fund_account("HYSA", 2000, 0, _utc(2024, 1, 1))
    planner.add_expense("Rent", ExpenseType.HOUSING, 1000, True, _utc(2024, 1, 1))

    required = planner.estimate_required_monthly_contribution(months_to_goal=0, target_months=3)
    assert required == pytest.approx(1000)


def test_estimate_required_monthly_contribution_rejects_negative_goal_months():
    planner = EmergencyFundPlanner()
    with pytest.raises(ValueError, match="months_to_goal"):
        planner.estimate_required_monthly_contribution(-1)


def test_estimate_required_monthly_contribution_returns_zero_if_already_on_target():
    planner = EmergencyFundPlanner()
    planner.set_fund_account("HYSA", 10000, 4, _utc(2024, 1, 1))
    planner.add_expense("Burn", ExpenseType.OTHER, 1000, True, _utc(2024, 1, 1))

    required = planner.estimate_required_monthly_contribution(months_to_goal=12, target_months=6)
    assert required == pytest.approx(0)


def test_estimate_required_monthly_contribution_with_growth():
    planner = EmergencyFundPlanner()
    planner.set_fund_account("HYSA", 1000, 12, _utc(2024, 1, 1))
    planner.add_expense("Burn", ExpenseType.OTHER, 1000, True, _utc(2024, 1, 1))

    required = planner.estimate_required_monthly_contribution(months_to_goal=5, target_months=3)
    assert required > 0
    assert required < 400  # growth lowers the straight-line amount below 400


def test_project_replenishment_rejects_invalid_inputs():
    planner = EmergencyFundPlanner()

    with pytest.raises(ValueError, match="monthly_contribution"):
        planner.project_replenishment(-1)

    with pytest.raises(ValueError, match="max_months"):
        planner.project_replenishment(100, max_months=-1)


def test_project_replenishment_reaches_target_without_yield():
    planner = EmergencyFundPlanner()
    planner.set_fund_account("HYSA", 0, 0, _utc(2024, 1, 1))
    planner.add_expense("Burn", ExpenseType.OTHER, 1000, True, _utc(2024, 1, 1))

    plan = planner.project_replenishment(monthly_contribution=500, target_months=2)

    assert isinstance(plan, ReplenishmentPlan)
    assert plan.target_reached is True
    assert plan.months_to_target == 4
    assert plan.projected_balance == pytest.approx(2000)
    assert len(plan.timeline) == 4


def test_project_replenishment_returns_none_date_if_not_reached():
    planner = EmergencyFundPlanner()
    planner.set_fund_account("HYSA", 0, 0, _utc(2024, 1, 1))
    planner.add_expense("Burn", ExpenseType.OTHER, 1000, True, _utc(2024, 1, 1))

    plan = planner.project_replenishment(monthly_contribution=100, target_months=3, max_months=2)

    assert plan.target_reached is False
    assert plan.projected_target_date is None
    assert plan.months_to_target == 2


def test_project_replenishment_tracks_yield_earned():
    planner = EmergencyFundPlanner()
    planner.set_fund_account("HYSA", 1000, 12, _utc(2024, 1, 1))
    planner.add_expense("Burn", ExpenseType.OTHER, 500, True, _utc(2024, 1, 1))

    plan = planner.project_replenishment(monthly_contribution=250, target_months=3)
    assert plan.yield_earned >= 0


def test_record_withdrawal_requires_account():
    planner = EmergencyFundPlanner()
    with pytest.raises(ValueError, match="fund account"):
        planner.record_withdrawal(100, "repair", _utc(2024, 1, 1))


def test_record_withdrawal_reduces_balance_and_caps_at_available_amount():
    planner = EmergencyFundPlanner()
    planner.set_fund_account("HYSA", 500, 4, _utc(2024, 1, 1))

    record = planner.record_withdrawal(700, "medical", _utc(2024, 2, 1))

    assert isinstance(record, WithdrawalRecord)
    assert record.amount == pytest.approx(500)
    assert planner.fund_account.current_balance == pytest.approx(0)
    assert len(planner.withdrawals) == 1


def test_record_withdrawal_rejects_negative_amount():
    planner = EmergencyFundPlanner()
    planner.set_fund_account("HYSA", 500, 4, _utc(2024, 1, 1))

    with pytest.raises(ValueError, match="amount"):
        planner.record_withdrawal(-1, "medical", _utc(2024, 2, 1))


def test_expense_to_dict_shape():
    expense = EmergencyExpense(
        expense_id="e1",
        name="Rent",
        expense_type=ExpenseType.HOUSING,
        monthly_amount=1000,
        essential=True,
        created_at=_utc(2024, 1, 1),
    )

    data = expense.to_dict()
    assert data["id"] == "e1"
    assert data["type"] == ExpenseType.HOUSING.value


def test_account_to_dict_shape():
    account = EmergencyFundAccount(
        account_id="a1",
        name="HYSA",
        current_balance=5000,
        annual_yield_pct=4,
        created_at=_utc(2024, 1, 1),
    )

    data = account.to_dict()
    assert data["id"] == "a1"
    assert data["current_balance"] == pytest.approx(5000)


def test_snapshot_to_dict_shape():
    planner = EmergencyFundPlanner()
    planner.set_fund_account("HYSA", 5000, 4, _utc(2024, 1, 1))
    planner.add_expense("Burn", ExpenseType.OTHER, 1000, True, _utc(2024, 1, 1))

    snapshot = planner.get_coverage_snapshot(target_months=6)
    data = snapshot.to_dict()

    assert data["health"] in [health.value for health in FundHealth]
    assert data["target_months"] == 6


def test_replenishment_plan_to_dict_shape():
    planner = EmergencyFundPlanner()
    planner.set_fund_account("HYSA", 0, 0, _utc(2024, 1, 1))
    planner.add_expense("Burn", ExpenseType.OTHER, 1000, True, _utc(2024, 1, 1))

    plan = planner.project_replenishment(monthly_contribution=500, target_months=2)
    data = plan.to_dict()

    assert data["target_reached"] is True
    assert len(data["timeline"]) == 4


def test_withdrawal_record_to_dict_shape():
    record = WithdrawalRecord(
        withdrawal_id="w1",
        amount=200,
        reason="car repair",
        withdrawn_at=_utc(2024, 2, 1),
    )

    data = record.to_dict()
    assert data["id"] == "w1"
    assert data["amount"] == pytest.approx(200)
