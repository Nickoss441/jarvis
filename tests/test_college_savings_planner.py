from datetime import datetime, timezone

import pytest

from jarvis.tools.college_savings_planner import (
    CollegeSavingsAccount,
    CollegeSavingsPlanner,
    ContributionPlan,
    EducationStage,
    FundingSnapshot,
    ReadinessStatus,
    SavingsAccountType,
    SavingsProjection,
    StudentProfile,
)


NOW = datetime(2026, 4, 27, tzinfo=timezone.utc)


class TestStudentProfile:
    def test_years_until_college(self):
        profile = StudentProfile(
            student_name="Ava",
            current_age=8,
            college_start_age=18,
            years_of_college=4,
            education_stage=EducationStage.IN_STATE_PUBLIC,
            education_inflation_pct=5,
            created_at=NOW,
        )
        assert profile.years_until_college == 10

    def test_rejects_inverted_ages(self):
        with pytest.raises(ValueError, match="college_start_age"):
            StudentProfile("Ava", 18, 17, 4, EducationStage.IN_STATE_PUBLIC, 5, NOW)

    def test_requires_timezone_aware_created_at(self):
        with pytest.raises(ValueError, match="timezone-aware"):
            StudentProfile(
                "Ava",
                8,
                18,
                4,
                EducationStage.IN_STATE_PUBLIC,
                5,
                datetime(2026, 4, 27),
            )


class TestCollegeSavingsAccount:
    def test_rejects_negative_balance(self):
        with pytest.raises(ValueError, match="current_balance"):
            CollegeSavingsAccount(SavingsAccountType.PLAN_529, -1, 1000, 6, NOW)

    def test_rejects_negative_annual_contribution(self):
        with pytest.raises(ValueError, match="annual_contribution"):
            CollegeSavingsAccount(SavingsAccountType.PLAN_529, 0, -1, 6, NOW)


class TestCollegeSavingsPlanner:
    def setup_method(self):
        self.planner = CollegeSavingsPlanner()
        self.planner.set_student_profile(
            student_name="Ava",
            current_age=8,
            college_start_age=18,
            years_of_college=4,
            education_stage=EducationStage.IN_STATE_PUBLIC,
            education_inflation_pct=5,
            created_at=NOW,
        )
        self.planner.set_savings_account(
            account_type=SavingsAccountType.PLAN_529,
            current_balance=20000,
            annual_contribution=6000,
            expected_return_pct=6,
            created_at=NOW,
        )

    def test_setters_register_objects(self):
        assert self.planner.student_profile.student_name == "Ava"
        assert self.planner.savings_account.current_balance == 20000

    def test_calculate_projected_total_cost_uses_stage_default(self):
        assert self.planner.calculate_projected_total_cost() == pytest.approx(175518.49)

    def test_calculate_projected_total_cost_with_override(self):
        assert self.planner.calculate_projected_total_cost(current_annual_cost=20000) == pytest.approx(140414.79)

    def test_calculate_projected_total_cost_rejects_negative_override(self):
        with pytest.raises(ValueError, match="current_annual_cost"):
            self.planner.calculate_projected_total_cost(current_annual_cost=-1)

    def test_project_savings_growth_defaults_to_years_until_college(self):
        projection = self.planner.project_savings_growth()
        assert isinstance(projection, SavingsProjection)
        assert projection.years == 10
        assert projection.ending_balance == pytest.approx(119646.81)
        assert projection.total_contributions == pytest.approx(60000)
        assert len(projection.timeline) == 10

    def test_project_savings_growth_rejects_negative_years(self):
        with pytest.raises(ValueError, match="years"):
            self.planner.project_savings_growth(years=-1)

    def test_estimate_required_monthly_contribution(self):
        plan = self.planner.estimate_required_monthly_contribution()
        assert isinstance(plan, ContributionPlan)
        assert plan.target_amount == pytest.approx(175518.49)
        assert plan.projected_shortfall_without_change == pytest.approx(55871.68)
        assert plan.monthly_contribution_required == pytest.approx(340.93)

    def test_estimate_required_monthly_contribution_zero_when_already_funded(self):
        self.planner.set_savings_account(
            account_type=SavingsAccountType.PLAN_529,
            current_balance=200000,
            annual_contribution=6000,
            expected_return_pct=6,
            created_at=NOW,
        )
        plan = self.planner.estimate_required_monthly_contribution()
        assert plan.projected_shortfall_without_change == pytest.approx(0)
        assert plan.monthly_contribution_required == pytest.approx(0)

    def test_get_funding_snapshot_underfunded(self):
        snapshot = self.planner.get_funding_snapshot()
        assert isinstance(snapshot, FundingSnapshot)
        assert snapshot.projected_savings_at_start == pytest.approx(119646.81)
        assert snapshot.funding_gap == pytest.approx(55871.68)
        assert snapshot.readiness_status == ReadinessStatus.UNDERFUNDED

    def test_get_funding_snapshot_on_track(self):
        self.planner.set_savings_account(
            account_type=SavingsAccountType.PLAN_529,
            current_balance=70000,
            annual_contribution=7000,
            expected_return_pct=6,
            created_at=NOW,
        )
        snapshot = self.planner.get_funding_snapshot()
        assert snapshot.readiness_status == ReadinessStatus.OVERFUNDED

    def test_get_funding_snapshot_fully_funded(self):
        self.planner.set_savings_account(
            account_type=SavingsAccountType.PLAN_529,
            current_balance=110000,
            annual_contribution=9000,
            expected_return_pct=6,
            created_at=NOW,
        )
        snapshot = self.planner.get_funding_snapshot()
        assert snapshot.readiness_status in {ReadinessStatus.FULLY_FUNDED, ReadinessStatus.OVERFUNDED}

    def test_requires_student_profile(self):
        planner = CollegeSavingsPlanner()
        with pytest.raises(ValueError, match="student_profile"):
            planner.calculate_projected_total_cost()

    def test_requires_savings_account(self):
        planner = CollegeSavingsPlanner()
        planner.set_student_profile("Ava", 8, 18, 4, EducationStage.IN_STATE_PUBLIC, 5, NOW)
        with pytest.raises(ValueError, match="savings_account"):
            planner.project_savings_growth()

    def test_to_dict_helpers(self):
        projection = self.planner.project_savings_growth()
        plan = self.planner.estimate_required_monthly_contribution()
        snapshot = self.planner.get_funding_snapshot()

        assert self.planner.student_profile.to_dict()["years_until_college"] == 10
        assert self.planner.savings_account.to_dict()["account_type"] == SavingsAccountType.PLAN_529.value
        assert projection.to_dict()["ending_balance"] == projection.ending_balance
        assert plan.to_dict()["monthly_contribution_required"] == plan.monthly_contribution_required
        assert snapshot.to_dict()["readiness_status"] == snapshot.readiness_status.value