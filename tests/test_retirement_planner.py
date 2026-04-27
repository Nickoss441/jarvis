from datetime import datetime, timezone

import pytest

from jarvis.tools.retirement_planner import (
    AccountType,
    ContributionCadence,
    ContributionPlan,
    RetirementAccount,
    RetirementPlanner,
    RetirementProjection,
    RiskProfile,
)


def _utc(year: int, month: int, day: int) -> datetime:
    return datetime(year, month, day, tzinfo=timezone.utc)


def test_retirement_account_validation_balance_negative():
    with pytest.raises(ValueError, match="current_balance"):
        RetirementAccount(
            account_id="a1",
            name="401k",
            account_type=AccountType.TRADITIONAL_401K,
            current_balance=-1,
            annual_contribution=1000,
            employer_match_rate=50,
            employer_match_cap_pct=6,
            created_at=_utc(2024, 1, 1),
        )


def test_retirement_account_validation_created_at_tz_aware():
    with pytest.raises(ValueError, match="timezone-aware"):
        RetirementAccount(
            account_id="a1",
            name="401k",
            account_type=AccountType.TRADITIONAL_401K,
            current_balance=100,
            annual_contribution=1000,
            employer_match_rate=50,
            employer_match_cap_pct=6,
            created_at=datetime(2024, 1, 1),
        )


def test_retirement_account_match_calculation():
    account = RetirementAccount(
        account_id="a1",
        name="401k",
        account_type=AccountType.TRADITIONAL_401K,
        current_balance=1000,
        annual_contribution=10000,
        employer_match_rate=50,
        employer_match_cap_pct=6,
        created_at=_utc(2024, 1, 1),
    )
    assert account.estimated_annual_match == pytest.approx(300)
    assert account.total_annual_addition == pytest.approx(10300)


def test_add_account_registers_account():
    planner = RetirementPlanner()
    account = planner.add_account(
        name="Roth IRA",
        account_type=AccountType.ROTH_IRA,
        current_balance=5000,
        annual_contribution=6500,
        employer_match_rate=0,
        employer_match_cap_pct=0,
        created_at=_utc(2024, 1, 1),
    )

    assert account.account_id in planner.accounts
    assert planner.accounts[account.account_id].name == "Roth IRA"


def test_total_balance_and_annual_contributions():
    planner = RetirementPlanner()
    planner.add_account("A", AccountType.ROTH_IRA, 5000, 1000, 0, 0, _utc(2024, 1, 1))
    planner.add_account("B", AccountType.TRADITIONAL_401K, 7000, 2000, 50, 4, _utc(2024, 1, 1))

    assert planner.get_total_balance() == pytest.approx(12000)
    expected_additions = 1000 + (2000 + (2000 * 0.04 * 0.5))
    assert planner.get_total_annual_contributions() == pytest.approx(expected_additions)


def test_default_return_assumption_by_risk_profile():
    planner = RetirementPlanner()

    assert planner.get_default_return_assumption(RiskProfile.CONSERVATIVE) == pytest.approx(4.5)
    assert planner.get_default_return_assumption(RiskProfile.MODERATE) == pytest.approx(6.5)
    assert planner.get_default_return_assumption(RiskProfile.AGGRESSIVE) == pytest.approx(8.5)


def test_project_retirement_growth_rejects_negative_years():
    planner = RetirementPlanner()
    with pytest.raises(ValueError, match="years"):
        planner.project_retirement_growth(years=-1)


def test_project_retirement_growth_rejects_invalid_inflation():
    planner = RetirementPlanner()
    with pytest.raises(ValueError, match="annual_inflation_pct"):
        planner.project_retirement_growth(years=10, annual_inflation_pct=-1)


def test_project_retirement_growth_no_accounts_zero_projection():
    planner = RetirementPlanner()
    projection = planner.project_retirement_growth(years=10)

    assert projection.starting_balance == pytest.approx(0)
    assert projection.ending_balance_nominal == pytest.approx(0)
    assert projection.total_contributions == pytest.approx(0)
    assert len(projection.timeline) == 10


def test_project_retirement_growth_with_custom_return_and_inflation():
    planner = RetirementPlanner()
    planner.add_account(
        name="401k",
        account_type=AccountType.TRADITIONAL_401K,
        current_balance=10000,
        annual_contribution=1000,
        employer_match_rate=0,
        employer_match_cap_pct=0,
        created_at=_utc(2024, 1, 1),
    )

    projection = planner.project_retirement_growth(
        years=2,
        annual_return_pct=0,
        annual_inflation_pct=5,
    )

    assert projection.ending_balance_nominal == pytest.approx(12000)
    assert projection.ending_balance_real < projection.ending_balance_nominal
    assert projection.total_contributions == pytest.approx(2000)


def test_project_retirement_growth_uses_risk_profile_default_when_return_omitted():
    planner = RetirementPlanner()
    planner.add_account(
        name="401k",
        account_type=AccountType.TRADITIONAL_401K,
        current_balance=1000,
        annual_contribution=100,
        employer_match_rate=0,
        employer_match_cap_pct=0,
        created_at=_utc(2024, 1, 1),
    )

    projection = planner.project_retirement_growth(years=1, risk_profile=RiskProfile.CONSERVATIVE)
    assert projection.annual_return_pct == pytest.approx(4.5)


def test_projection_timeline_growth_fields_consistent():
    planner = RetirementPlanner()
    planner.add_account(
        name="IRA",
        account_type=AccountType.ROTH_IRA,
        current_balance=1000,
        annual_contribution=100,
        employer_match_rate=0,
        employer_match_cap_pct=0,
        created_at=_utc(2024, 1, 1),
    )

    projection = planner.project_retirement_growth(years=3, annual_return_pct=0)

    assert projection.timeline[-1].projected_balance == pytest.approx(1300)
    assert projection.timeline[-1].cumulative_contributions == pytest.approx(300)
    assert projection.timeline[-1].cumulative_growth == pytest.approx(0)


def test_estimate_required_contribution_rejects_negative_target_or_years():
    planner = RetirementPlanner()

    with pytest.raises(ValueError, match="target_amount"):
        planner.estimate_required_contribution(
            target_amount=-1,
            years_to_target=10,
            cadence=ContributionCadence.MONTHLY,
        )

    with pytest.raises(ValueError, match="years_to_target"):
        planner.estimate_required_contribution(
            target_amount=100000,
            years_to_target=-2,
            cadence=ContributionCadence.MONTHLY,
        )


def test_estimate_required_contribution_zero_years_uses_gap():
    planner = RetirementPlanner()
    planner.add_account(
        name="Existing",
        account_type=AccountType.ROTH_IRA,
        current_balance=40000,
        annual_contribution=0,
        employer_match_rate=0,
        employer_match_cap_pct=0,
        created_at=_utc(2024, 1, 1),
    )

    plan = planner.estimate_required_contribution(
        target_amount=50000,
        years_to_target=0,
        cadence=ContributionCadence.MONTHLY,
        annual_return_pct=7,
    )

    assert plan.required_contribution_per_period == pytest.approx(10000)


def test_estimate_required_contribution_when_already_on_target_is_zero():
    planner = RetirementPlanner()
    planner.add_account(
        name="Existing",
        account_type=AccountType.ROTH_IRA,
        current_balance=100000,
        annual_contribution=0,
        employer_match_rate=0,
        employer_match_cap_pct=0,
        created_at=_utc(2024, 1, 1),
    )

    plan = planner.estimate_required_contribution(
        target_amount=50000,
        years_to_target=10,
        cadence=ContributionCadence.MONTHLY,
        annual_return_pct=6,
    )

    assert plan.required_contribution_per_period == pytest.approx(0)


def test_estimate_required_contribution_returns_plan_object_and_periods():
    planner = RetirementPlanner()
    plan = planner.estimate_required_contribution(
        target_amount=500000,
        years_to_target=20,
        cadence=ContributionCadence.BIWEEKLY,
        annual_return_pct=7,
    )

    assert isinstance(plan, ContributionPlan)
    assert plan.periods_per_year == 26
    assert plan.required_contribution_per_period >= 0


def test_estimate_required_contribution_uses_risk_profile_default():
    planner = RetirementPlanner()
    plan = planner.estimate_required_contribution(
        target_amount=300000,
        years_to_target=20,
        cadence=ContributionCadence.MONTHLY,
        risk_profile=RiskProfile.AGGRESSIVE,
    )

    assert plan.annual_return_pct == pytest.approx(8.5)


def test_estimate_safe_withdrawal_income_validation():
    planner = RetirementPlanner()

    with pytest.raises(ValueError, match="withdrawal_rate_pct"):
        planner.estimate_safe_withdrawal_income(withdrawal_rate_pct=-1)

    with pytest.raises(ValueError, match="annual_tax_drag_pct"):
        planner.estimate_safe_withdrawal_income(annual_tax_drag_pct=101)


def test_estimate_safe_withdrawal_income_calculation():
    planner = RetirementPlanner()
    planner.add_account(
        name="401k",
        account_type=AccountType.TRADITIONAL_401K,
        current_balance=1000000,
        annual_contribution=0,
        employer_match_rate=0,
        employer_match_cap_pct=0,
        created_at=_utc(2024, 1, 1),
    )

    income = planner.estimate_safe_withdrawal_income(withdrawal_rate_pct=4, annual_tax_drag_pct=20)

    assert income["gross_annual_income"] == pytest.approx(40000)
    assert income["gross_monthly_income"] == pytest.approx(3333.33, abs=0.01)
    assert income["net_annual_income"] == pytest.approx(32000)
    assert income["net_monthly_income"] == pytest.approx(2666.67, abs=0.01)


def test_to_real_dollars_helper_edge_cases():
    planner = RetirementPlanner()

    assert planner._to_real_dollars(1000, 0, 10) == pytest.approx(1000)
    assert planner._to_real_dollars(1000, 3, 0) == pytest.approx(1000)
    assert planner._to_real_dollars(1000, 3, 10) < 1000


def test_account_to_dict_shape():
    account = RetirementAccount(
        account_id="a1",
        name="IRA",
        account_type=AccountType.ROTH_IRA,
        current_balance=1000,
        annual_contribution=500,
        employer_match_rate=0,
        employer_match_cap_pct=0,
        created_at=_utc(2024, 1, 1),
    )

    data = account.to_dict()
    assert data["id"] == "a1"
    assert data["type"] == AccountType.ROTH_IRA.value


def test_projection_to_dict_shape():
    planner = RetirementPlanner()
    planner.add_account(
        name="IRA",
        account_type=AccountType.ROTH_IRA,
        current_balance=1000,
        annual_contribution=100,
        employer_match_rate=0,
        employer_match_cap_pct=0,
        created_at=_utc(2024, 1, 1),
    )

    projection = planner.project_retirement_growth(years=2, annual_return_pct=0)
    data = projection.to_dict()

    assert isinstance(projection, RetirementProjection)
    assert data["years"] == 2
    assert len(data["timeline"]) == 2


def test_contribution_plan_to_dict_shape():
    planner = RetirementPlanner()
    plan = planner.estimate_required_contribution(
        target_amount=100000,
        years_to_target=10,
        cadence=ContributionCadence.QUARTERLY,
        annual_return_pct=5,
    )

    data = plan.to_dict()
    assert data["cadence"] == ContributionCadence.QUARTERLY.value
    assert data["periods_per_year"] == 4


def test_project_retirement_growth_rejects_non_finite_return():
    planner = RetirementPlanner()

    with pytest.raises(ValueError, match="annual_return_pct"):
        planner.project_retirement_growth(years=5, annual_return_pct=float("inf"))


def test_estimate_required_contribution_rejects_non_finite_return():
    planner = RetirementPlanner()

    with pytest.raises(ValueError, match="annual_return_pct"):
        planner.estimate_required_contribution(
            target_amount=100000,
            years_to_target=10,
            cadence=ContributionCadence.MONTHLY,
            annual_return_pct=float("nan"),
        )


def test_projection_and_plan_ids_are_generated():
    planner = RetirementPlanner()
    projection = planner.project_retirement_growth(years=1)
    plan = planner.estimate_required_contribution(
        target_amount=10000,
        years_to_target=1,
        cadence=ContributionCadence.ANNUAL,
    )

    assert isinstance(projection.projection_id, str)
    assert isinstance(plan.plan_id, str)
    assert len(projection.projection_id) > 0
    assert len(plan.plan_id) > 0
