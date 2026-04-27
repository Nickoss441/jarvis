from datetime import datetime, timezone

import pytest

from jarvis.tools.rent_vs_buy_analyzer import (
    BuyScenario,
    ComparisonYear,
    Recommendation,
    RentBuyAnalysis,
    RentScenario,
    RentVsBuyAnalyzer,
)


NOW = datetime(2026, 4, 27, tzinfo=timezone.utc)


class TestRentScenario:
    def test_rejects_negative_monthly_rent(self):
        with pytest.raises(ValueError, match="monthly_rent"):
            RentScenario(-1, 3, 120, 1000, NOW)

    def test_requires_timezone_aware_created_at(self):
        with pytest.raises(ValueError, match="timezone-aware"):
            RentScenario(2000, 3, 120, 1000, datetime(2026, 4, 27))


class TestBuyScenario:
    def test_down_payment_and_loan_amount(self):
        scenario = BuyScenario(
            home_price=400000,
            down_payment_pct=20,
            mortgage_rate_pct=6.5,
            mortgage_term_years=30,
            property_tax_rate_pct=1.2,
            annual_home_insurance=1800,
            annual_maintenance_pct=1.0,
            monthly_hoa=150,
            closing_cost_pct=3,
            expected_appreciation_pct=3,
            selling_cost_pct=6,
            created_at=NOW,
        )
        assert scenario.down_payment_amount == pytest.approx(80000)
        assert scenario.loan_amount == pytest.approx(320000)
        assert scenario.closing_cost_amount == pytest.approx(12000)

    def test_rejects_invalid_down_payment_pct(self):
        with pytest.raises(ValueError, match="down_payment_pct"):
            BuyScenario(1, 101, 6, 30, 1, 1000, 1, 0, 3, 3, 6, NOW)


class TestRentVsBuyAnalyzer:
    def setup_method(self):
        self.analyzer = RentVsBuyAnalyzer()
        self.analyzer.set_rent_scenario(
            monthly_rent=2400,
            annual_rent_increase_pct=3,
            annual_renters_insurance=240,
            upfront_move_in_cost=2400,
            created_at=NOW,
        )
        self.analyzer.set_buy_scenario(
            home_price=400000,
            down_payment_pct=20,
            mortgage_rate_pct=6.5,
            mortgage_term_years=30,
            property_tax_rate_pct=1.2,
            annual_home_insurance=1800,
            annual_maintenance_pct=1.0,
            monthly_hoa=150,
            closing_cost_pct=3,
            expected_appreciation_pct=3,
            selling_cost_pct=6,
            created_at=NOW,
        )

    def test_calculate_monthly_mortgage_payment(self):
        assert self.analyzer.calculate_monthly_mortgage_payment() == pytest.approx(2022.61, rel=1e-4)

    def test_calculate_monthly_mortgage_payment_zero_interest(self):
        analyzer = RentVsBuyAnalyzer()
        analyzer.set_buy_scenario(120000, 20, 0, 30, 1.0, 1200, 1.0, 0, 3, 2, 6, NOW)
        assert analyzer.calculate_monthly_mortgage_payment() == pytest.approx(266.67, rel=1e-4)

    def test_estimate_initial_cash_required(self):
        assert self.analyzer.estimate_initial_cash_required() == pytest.approx(92000)

    def test_requires_scenarios_for_analysis(self):
        analyzer = RentVsBuyAnalyzer()
        with pytest.raises(ValueError, match="rent_scenario"):
            analyzer.analyze(5)

        analyzer.set_rent_scenario(2000, 3, 120, 1000, NOW)
        with pytest.raises(ValueError, match="buy_scenario"):
            analyzer.analyze(5)

    def test_rejects_negative_years(self):
        with pytest.raises(ValueError, match="years"):
            self.analyzer.analyze(-1)

    def test_analyze_returns_analysis(self):
        analysis = self.analyzer.analyze(7)
        assert isinstance(analysis, RentBuyAnalysis)
        assert len(analysis.timeline) == 7
        assert isinstance(analysis.timeline[0], ComparisonYear)
        assert analysis.initial_cash_required == pytest.approx(92000)

    def test_buy_recommended_on_long_horizon(self):
        analysis = self.analyzer.analyze(10)
        assert analysis.recommendation == Recommendation.BUY
        assert analysis.break_even_year is not None
        assert analysis.ending_equity > 0
        assert analysis.ending_effective_buy_cost < analysis.total_rent_cost

    def test_rent_recommended_on_short_horizon_with_high_friction(self):
        analyzer = RentVsBuyAnalyzer()
        analyzer.set_rent_scenario(2200, 2, 240, 2200, NOW)
        analyzer.set_buy_scenario(
            home_price=500000,
            down_payment_pct=10,
            mortgage_rate_pct=7.2,
            mortgage_term_years=30,
            property_tax_rate_pct=1.4,
            annual_home_insurance=2400,
            annual_maintenance_pct=1.5,
            monthly_hoa=250,
            closing_cost_pct=4,
            expected_appreciation_pct=1,
            selling_cost_pct=7,
            created_at=NOW,
        )
        analysis = analyzer.analyze(3)
        assert analysis.recommendation == Recommendation.RENT
        assert analysis.break_even_year is None
        assert analysis.ending_effective_buy_cost > analysis.total_rent_cost

    def test_zero_year_analysis(self):
        analysis = self.analyzer.analyze(0)
        assert analysis.years == 0
        assert analysis.timeline == []
        assert analysis.total_rent_cost == pytest.approx(2400)
        assert analysis.ending_mortgage_balance == pytest.approx(320000)

    def test_rent_cost_grows_each_year(self):
        analysis = self.analyzer.analyze(4)
        assert analysis.timeline[1].cumulative_rent_cost > analysis.timeline[0].cumulative_rent_cost

    def test_remaining_mortgage_balance_declines(self):
        analysis = self.analyzer.analyze(4)
        assert analysis.timeline[1].remaining_mortgage_balance < analysis.timeline[0].remaining_mortgage_balance

    def test_net_sale_proceeds_improve_over_time(self):
        analysis = self.analyzer.analyze(8)
        assert analysis.timeline[-1].net_sale_proceeds > analysis.timeline[0].net_sale_proceeds

    def test_to_dict_helpers(self):
        analysis = self.analyzer.analyze(5)
        assert self.analyzer.rent_scenario.to_dict()["monthly_rent"] == pytest.approx(2400)
        assert self.analyzer.buy_scenario.to_dict()["loan_amount"] == pytest.approx(320000)
        data = analysis.to_dict()
        assert data["recommendation"] == analysis.recommendation.value
        assert len(data["timeline"]) == 5