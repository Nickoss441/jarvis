from datetime import datetime, timezone

import pytest

from jarvis.tools.financial_independence_planner import (
    ExpenseProfile,
    FinancialIndependencePlanner,
    IncomeProfile,
    IndependenceProjection,
    IndependenceSnapshot,
    InvestmentPortfolio,
    LifestyleProfile,
)


NOW = datetime(2026, 4, 27, tzinfo=timezone.utc)


class TestIncomeProfile:
    def test_annual_income(self):
        profile = IncomeProfile(monthly_income=6000, annual_bonus=12000, created_at=NOW)
        assert profile.annual_income == 84000

    def test_rejects_negative_monthly_income(self):
        with pytest.raises(ValueError, match="monthly_income"):
            IncomeProfile(monthly_income=-1, annual_bonus=0, created_at=NOW)

    def test_requires_timezone_aware_created_at(self):
        with pytest.raises(ValueError, match="timezone-aware"):
            IncomeProfile(monthly_income=1, annual_bonus=0, created_at=datetime(2026, 4, 27))


class TestExpenseProfile:
    def test_annual_expenses(self):
        profile = ExpenseProfile(
            essential_monthly=2500,
            discretionary_monthly=500,
            annual_irregular=2400,
            lifestyle_profile=LifestyleProfile.STANDARD,
            created_at=NOW,
        )
        assert profile.annual_expenses == 38400

    def test_rejects_negative_annual_irregular(self):
        with pytest.raises(ValueError, match="annual_irregular"):
            ExpenseProfile(
                essential_monthly=1,
                discretionary_monthly=1,
                annual_irregular=-1,
                lifestyle_profile=LifestyleProfile.LEAN,
                created_at=NOW,
            )


class TestInvestmentPortfolio:
    def test_rejects_invalid_safe_withdrawal_rate(self):
        with pytest.raises(ValueError, match="safe_withdrawal_rate_pct"):
            InvestmentPortfolio(
                invested_assets=1000,
                annual_return_pct=7,
                safe_withdrawal_rate_pct=0,
                created_at=NOW,
            )


class TestFinancialIndependencePlanner:
    def setup_method(self):
        self.planner = FinancialIndependencePlanner()
        self.planner.set_income_profile(monthly_income=7000, annual_bonus=10000, created_at=NOW)
        self.planner.set_expense_profile(
            essential_monthly=2800,
            discretionary_monthly=700,
            annual_irregular=3600,
            lifestyle_profile=LifestyleProfile.STANDARD,
            created_at=NOW,
        )
        self.planner.set_portfolio(
            invested_assets=150000,
            annual_return_pct=7,
            safe_withdrawal_rate_pct=4,
            created_at=NOW,
        )

    def test_get_annual_savings_capacity(self):
        assert self.planner.get_annual_savings_capacity() == 48400

    def test_get_savings_rate(self):
        assert self.planner.get_savings_rate() == pytest.approx(51.4893617021)

    def test_calculate_fi_number(self):
        assert self.planner.calculate_fi_number() == 1140000.0

    def test_calculate_fi_number_with_override(self):
        assert self.planner.calculate_fi_number(annual_expenses_override=50000, withdrawal_rate_override_pct=5) == 1000000.0

    def test_rejects_negative_expense_override(self):
        with pytest.raises(ValueError, match="annual_expenses"):
            self.planner.calculate_fi_number(annual_expenses_override=-1)

    def test_calculate_coast_fi_number(self):
        coast = self.planner.calculate_coast_fi_number(current_age=35, retirement_age=60)
        assert coast == pytest.approx(210044.06, rel=1e-6)

    def test_calculate_coast_fi_number_same_age(self):
        assert self.planner.calculate_coast_fi_number(current_age=60, retirement_age=60) == 1140000.0

    def test_rejects_inverted_retirement_ages(self):
        with pytest.raises(ValueError, match="retirement_age"):
            self.planner.calculate_coast_fi_number(current_age=50, retirement_age=40)

    def test_get_independence_snapshot(self):
        snapshot = self.planner.get_independence_snapshot(current_age=35, retirement_age=60)
        assert isinstance(snapshot, IndependenceSnapshot)
        assert snapshot.annual_income == 94000
        assert snapshot.annual_expenses == 45600
        assert snapshot.annual_savings == 48400
        assert snapshot.savings_rate_pct == pytest.approx(51.49, rel=1e-3)
        assert snapshot.fi_progress_pct == pytest.approx(13.16, rel=1e-3)
        assert snapshot.coast_fi_number == pytest.approx(210044.06, rel=1e-6)

    def test_estimate_required_monthly_investment(self):
        required = self.planner.estimate_required_monthly_investment(target_years=15)
        assert required == pytest.approx(2248.4, rel=1e-6)

    def test_estimate_required_monthly_investment_zero_if_already_covered(self):
        self.planner.set_portfolio(
            invested_assets=2_000_000,
            annual_return_pct=7,
            safe_withdrawal_rate_pct=4,
            created_at=NOW,
        )
        assert self.planner.estimate_required_monthly_investment(target_years=10) == 0.0

    def test_estimate_required_monthly_investment_zero_years(self):
        required = self.planner.estimate_required_monthly_investment(target_years=0)
        assert required == 990000.0

    def test_rejects_negative_target_years(self):
        with pytest.raises(ValueError, match="target_years"):
            self.planner.estimate_required_monthly_investment(target_years=-1)

    def test_project_to_financial_independence(self):
        projection = self.planner.project_to_financial_independence(monthly_investment=2500, max_years=30)
        assert isinstance(projection, IndependenceProjection)
        assert projection.target_reached is True
        assert projection.years_to_fi == 15
        assert projection.projected_balance == pytest.approx(1220496.34, rel=1e-6)
        assert len(projection.timeline) == 15
        assert projection.projected_fi_date is not None

    def test_projection_can_fail_to_reach_target(self):
        projection = self.planner.project_to_financial_independence(monthly_investment=100, max_years=5)
        assert projection.target_reached is False
        assert projection.years_to_fi == 5
        assert projection.projected_fi_date is None
        assert len(projection.timeline) == 5

    def test_rejects_negative_monthly_investment(self):
        with pytest.raises(ValueError, match="monthly_investment"):
            self.planner.project_to_financial_independence(monthly_investment=-1)

    def test_snapshot_defaults_when_profiles_missing(self):
        planner = FinancialIndependencePlanner()
        snapshot = planner.get_independence_snapshot()
        assert snapshot.annual_income == 0
        assert snapshot.annual_expenses == 0
        assert snapshot.fi_number == 0
        assert snapshot.fi_progress_pct == 100.0
        assert snapshot.coast_fi_number == 0

    def test_projection_to_dict(self):
        projection = self.planner.project_to_financial_independence(monthly_investment=2500, max_years=30)
        data = projection.to_dict()
        assert data["id"] == projection.projection_id
        assert data["target_reached"] is True
        assert len(data["timeline"]) == len(projection.timeline)

    def test_snapshot_to_dict(self):
        snapshot = self.planner.get_independence_snapshot()
        data = snapshot.to_dict()
        assert data["fi_number"] == snapshot.fi_number
        assert data["portfolio_balance"] == snapshot.portfolio_balance

    def test_profiles_to_dict(self):
        assert self.planner.income_profile.to_dict()["annual_income"] == 94000
        assert self.planner.expense_profile.to_dict()["annual_expenses"] == 45600
        assert self.planner.portfolio.to_dict()["invested_assets"] == 150000
