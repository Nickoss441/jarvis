from datetime import datetime, timezone

import pytest

from jarvis.tools.home_purchase_planner import (
    AffordabilityBand,
    AffordabilitySnapshot,
    ClosingCostEstimate,
    DownPaymentPlan,
    HomePurchasePlanner,
    MortgageScenario,
    PropertyType,
    PurchaseProfile,
)


NOW = datetime(2026, 4, 27, tzinfo=timezone.utc)


class TestPurchaseProfile:
    def test_monthly_housing_budget(self):
        profile = PurchaseProfile(
            gross_annual_income=120000,
            monthly_debt_payments=500,
            available_cash=90000,
            desired_down_payment_pct=20,
            target_housing_ratio_pct=28,
            created_at=NOW,
        )
        assert profile.gross_monthly_income == 10000
        assert profile.monthly_housing_budget == 2300

    def test_rejects_negative_income(self):
        with pytest.raises(ValueError, match="gross_annual_income"):
            PurchaseProfile(-1, 0, 0, 20, 28, NOW)

    def test_requires_timezone_aware_created_at(self):
        with pytest.raises(ValueError, match="timezone-aware"):
            PurchaseProfile(1, 0, 0, 20, 28, datetime(2026, 4, 27))


class TestMortgageScenario:
    def test_monthly_cost_components(self):
        scenario = MortgageScenario(
            scenario_id="m1",
            property_price=400000,
            property_type=PropertyType.SINGLE_FAMILY,
            down_payment=80000,
            loan_amount=320000,
            annual_interest_rate_pct=6.5,
            loan_term_years=30,
            property_tax_rate_pct=1.2,
            annual_home_insurance=1800,
            monthly_hoa=150,
            private_mortgage_insurance_pct=0.8,
            created_at=NOW,
        )
        assert scenario.down_payment_pct == pytest.approx(20)
        assert scenario.monthly_principal_interest == pytest.approx(2022.61, rel=1e-4)
        assert scenario.monthly_property_tax == pytest.approx(400)
        assert scenario.monthly_home_insurance == pytest.approx(150)
        assert scenario.monthly_pmi == pytest.approx(0)
        assert scenario.total_monthly_housing_cost == pytest.approx(2722.61, rel=1e-4)

    def test_pmi_applies_below_twenty_percent_down(self):
        scenario = MortgageScenario(
            scenario_id="m2",
            property_price=300000,
            property_type=PropertyType.CONDO,
            down_payment=15000,
            loan_amount=285000,
            annual_interest_rate_pct=6,
            loan_term_years=30,
            property_tax_rate_pct=1,
            annual_home_insurance=1200,
            monthly_hoa=100,
            private_mortgage_insurance_pct=1,
            created_at=NOW,
        )
        assert scenario.monthly_pmi == pytest.approx(237.5)

    def test_rejects_invalid_term(self):
        with pytest.raises(ValueError, match="loan_term_years"):
            MortgageScenario(
                scenario_id="m3",
                property_price=1,
                property_type=PropertyType.SINGLE_FAMILY,
                down_payment=0,
                loan_amount=1,
                annual_interest_rate_pct=6,
                loan_term_years=0,
                property_tax_rate_pct=1,
                annual_home_insurance=1,
                monthly_hoa=0,
                private_mortgage_insurance_pct=0,
                created_at=NOW,
            )


class TestHomePurchasePlanner:
    def setup_method(self):
        self.planner = HomePurchasePlanner()
        self.planner.set_purchase_profile(
            gross_annual_income=120000,
            monthly_debt_payments=500,
            available_cash=90000,
            desired_down_payment_pct=20,
            target_housing_ratio_pct=28,
            created_at=NOW,
        )

    def test_set_purchase_profile_registers_profile(self):
        assert self.planner.purchase_profile is not None
        assert self.planner.purchase_profile.available_cash == 90000

    def test_build_mortgage_scenario_uses_profile_down_payment(self):
        scenario = self.planner.build_mortgage_scenario(
            property_price=350000,
            annual_interest_rate_pct=6.5,
            loan_term_years=30,
            property_tax_rate_pct=1.1,
            annual_home_insurance=1500,
        )
        assert isinstance(scenario, MortgageScenario)
        assert scenario.down_payment == pytest.approx(70000)
        assert scenario.loan_amount == pytest.approx(280000)

    def test_build_mortgage_scenario_rejects_invalid_down_payment_pct(self):
        with pytest.raises(ValueError, match="down_payment_pct"):
            self.planner.build_mortgage_scenario(
                property_price=300000,
                annual_interest_rate_pct=6,
                loan_term_years=30,
                property_tax_rate_pct=1,
                annual_home_insurance=1200,
                down_payment_pct=120,
            )

    def test_estimate_closing_costs(self):
        estimate = self.planner.estimate_closing_costs(400000, closing_cost_pct=3)
        assert isinstance(estimate, ClosingCostEstimate)
        assert estimate.down_payment == pytest.approx(80000)
        assert estimate.estimated_closing_costs == pytest.approx(12000)
        assert estimate.total_cash_required == pytest.approx(92000)

    def test_estimate_closing_costs_rejects_invalid_pct(self):
        with pytest.raises(ValueError, match="closing_cost_pct"):
            self.planner.estimate_closing_costs(100000, closing_cost_pct=-1)

    def test_estimate_max_home_price(self):
        max_price = self.planner.estimate_max_home_price(
            annual_interest_rate_pct=6.5,
            loan_term_years=30,
            property_tax_rate_pct=1.2,
            annual_home_insurance=1800,
            monthly_hoa=150,
            private_mortgage_insurance_pct=0.8,
        )
        assert max_price == pytest.approx(330221.32, rel=1e-5)

    def test_estimate_max_home_price_requires_profile(self):
        planner = HomePurchasePlanner()
        with pytest.raises(ValueError, match="purchase_profile"):
            planner.estimate_max_home_price(6.5, 30, 1.2, 1800)

    def test_project_down_payment_timeline(self):
        plan = self.planner.project_down_payment_timeline(
            target_home_price=450000,
            monthly_savings=2500,
            closing_cost_pct=3,
        )
        assert isinstance(plan, DownPaymentPlan)
        assert plan.required_down_payment == pytest.approx(90000)
        assert plan.estimated_closing_costs == pytest.approx(13500)
        assert plan.total_cash_needed == pytest.approx(103500)
        assert plan.cash_gap == pytest.approx(13500)
        assert plan.months_to_target == 6
        assert plan.target_date is not None

    def test_project_down_payment_timeline_when_already_funded(self):
        plan = self.planner.project_down_payment_timeline(
            target_home_price=300000,
            monthly_savings=1000,
            closing_cost_pct=2,
        )
        assert plan.cash_gap == pytest.approx(0)
        assert plan.months_to_target == 0
        assert plan.target_date is not None

    def test_project_down_payment_timeline_without_monthly_savings(self):
        plan = self.planner.project_down_payment_timeline(
            target_home_price=500000,
            monthly_savings=0,
            closing_cost_pct=3,
        )
        assert plan.cash_gap > 0
        assert plan.months_to_target is None
        assert plan.target_date is None

    def test_project_down_payment_timeline_rejects_negative_monthly_savings(self):
        with pytest.raises(ValueError, match="monthly_savings"):
            self.planner.project_down_payment_timeline(400000, -1)

    def test_get_affordability_snapshot(self):
        snapshot = self.planner.get_affordability_snapshot(
            annual_interest_rate_pct=6.5,
            loan_term_years=30,
            property_tax_rate_pct=1.2,
            annual_home_insurance=1800,
            monthly_hoa=150,
            private_mortgage_insurance_pct=0.8,
        )
        assert isinstance(snapshot, AffordabilitySnapshot)
        assert snapshot.monthly_housing_budget == pytest.approx(2300)
        assert snapshot.cash_limited_price == pytest.approx(391304.35, rel=1e-5)
        assert snapshot.income_limited_price == pytest.approx(330221.32, rel=1e-5)
        assert snapshot.recommended_budget == pytest.approx(330221.32, rel=1e-5)
        assert snapshot.affordability_band == AffordabilityBand.COMFORTABLE

    def test_get_affordability_snapshot_comfortable_band(self):
        planner = HomePurchasePlanner()
        planner.set_purchase_profile(200000, 0, 200000, 30, 20, NOW)
        snapshot = planner.get_affordability_snapshot(5.5, 30, 1.0, 1500)
        assert snapshot.affordability_band == AffordabilityBand.BALANCED

    def test_to_dict_helpers(self):
        scenario = self.planner.build_mortgage_scenario(
            property_price=350000,
            annual_interest_rate_pct=6.5,
            loan_term_years=30,
            property_tax_rate_pct=1.1,
            annual_home_insurance=1500,
        )
        estimate = self.planner.estimate_closing_costs(350000)
        plan = self.planner.project_down_payment_timeline(350000, 1500)
        snapshot = self.planner.get_affordability_snapshot(6.5, 30, 1.2, 1800)

        assert self.planner.purchase_profile.to_dict()["monthly_housing_budget"] == pytest.approx(2300)
        assert scenario.to_dict()["property_type"] == PropertyType.SINGLE_FAMILY.value
        assert estimate.to_dict()["total_cash_required"] > 0
        assert plan.to_dict()["current_cash"] == pytest.approx(90000)
        assert snapshot.to_dict()["affordability_band"] == snapshot.affordability_band.value