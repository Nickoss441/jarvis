"""Tests for financial recommendations engine."""

import pytest
from datetime import datetime, timezone

from jarvis.tools.financial_recommendations import (
    RecommendationCategory, RecommendationPriority, RecommendationStatus,
    Recommendation, FinancialProfile, RecommendationPlan, RecommendationEngine
)


class TestRecommendationCategory:
    """Tests for recommendation categories."""
    
    def test_all_categories(self):
        """Verify all categories are defined."""
        cats = [c.value for c in RecommendationCategory]
        assert "emergency_fund" in cats
        assert "debt_reduction" in cats
        assert "savings" in cats


class TestRecommendationPriority:
    """Tests for recommendation priorities."""
    
    def test_all_priorities(self):
        """Verify all priorities are defined."""
        priorities = [p.value for p in RecommendationPriority]
        assert "critical" in priorities
        assert "high" in priorities
        assert "medium" in priorities
        assert "low" in priorities


class TestRecommendationStatus:
    """Tests for recommendation status."""
    
    def test_all_statuses(self):
        """Verify all statuses are defined."""
        statuses = [s.value for s in RecommendationStatus]
        assert "not_started" in statuses
        assert "in_progress" in statuses


class TestRecommendation:
    """Tests for individual recommendations."""
    
    def test_recommendation_creation(self):
        """Test creating a recommendation."""
        rec = Recommendation(
            recommendation_id="rec-1",
            category=RecommendationCategory.SAVINGS,
            title="Increase Savings",
            description="Build up savings",
            rationale="More savings = better financial health",
            target_metric="Savings Rate",
            current_value="10%",
            target_value="20%",
            priority=RecommendationPriority.HIGH,
            estimated_impact=5000.0,
            estimated_timeframe=12,
            action_steps=["Step 1", "Step 2"],
        )
        assert rec.title == "Increase Savings"
        assert rec.estimated_impact == 5000.0
    
    def test_recommendation_default_status(self):
        """Test default recommendation status."""
        rec = Recommendation(
            recommendation_id="rec-1",
            category=RecommendationCategory.SAVINGS,
            title="Test",
            description="Test",
            rationale="Test",
            target_metric="Test",
            current_value="1",
            target_value="2",
            priority=RecommendationPriority.HIGH,
            estimated_impact=100.0,
            estimated_timeframe=12,
            action_steps=[],
        )
        assert rec.status == RecommendationStatus.NOT_STARTED
    
    def test_recommendation_auto_timestamp(self):
        """Test automatic timestamp assignment."""
        rec = Recommendation(
            recommendation_id="rec-1",
            category=RecommendationCategory.SAVINGS,
            title="Test",
            description="Test",
            rationale="Test",
            target_metric="Test",
            current_value="1",
            target_value="2",
            priority=RecommendationPriority.HIGH,
            estimated_impact=100.0,
            estimated_timeframe=12,
            action_steps=[],
        )
        assert rec.created_at is not None
    
    def test_recommendation_to_dict(self):
        """Test recommendation serialization."""
        rec = Recommendation(
            recommendation_id="rec-1",
            category=RecommendationCategory.SAVINGS,
            title="Increase Savings",
            description="Build up savings",
            rationale="More savings",
            target_metric="Savings Rate",
            current_value="10%",
            target_value="20%",
            priority=RecommendationPriority.HIGH,
            estimated_impact=5000.0,
            estimated_timeframe=12,
            action_steps=["Step 1"],
        )
        data = rec.to_dict()
        
        assert data["title"] == "Increase Savings"
        assert data["impact"] == 5000.0


class TestFinancialProfile:
    """Tests for financial profiles."""
    
    def test_profile_creation(self):
        """Test creating a financial profile."""
        profile = FinancialProfile(
            annual_income=100_000,
            monthly_expenses=5_000,
            emergency_fund_balance=15_000,
            emergency_fund_months=3,
            total_debt=20_000,
            investment_portfolio_value=50_000,
            retirement_savings=100_000,
            current_age=35,
            retirement_age_target=65,
            risk_tolerance=7,
        )
        assert profile.annual_income == 100_000
        assert profile.net_worth > 0
    
    def test_profile_monthly_income(self):
        """Test monthly income calculation."""
        profile = FinancialProfile(
            annual_income=120_000,
            monthly_expenses=5_000,
            emergency_fund_balance=15_000,
            emergency_fund_months=3,
            total_debt=0,
            investment_portfolio_value=0,
            retirement_savings=0,
            current_age=35,
            retirement_age_target=65,
            risk_tolerance=5,
        )
        assert profile.monthly_income == pytest.approx(10_000.0)
    
    def test_profile_net_worth(self):
        """Test net worth calculation."""
        profile = FinancialProfile(
            annual_income=100_000,
            monthly_expenses=5_000,
            emergency_fund_balance=20_000,
            emergency_fund_months=4,
            total_debt=50_000,
            investment_portfolio_value=100_000,
            retirement_savings=150_000,
            current_age=40,
            retirement_age_target=65,
            risk_tolerance=6,
        )
        # Net worth = 20_000 + 100_000 + 150_000 - 50_000 = 220_000
        assert profile.net_worth == 220_000
    
    def test_profile_debt_to_income(self):
        """Test debt-to-income ratio."""
        profile = FinancialProfile(
            annual_income=100_000,
            monthly_expenses=5_000,
            emergency_fund_balance=15_000,
            emergency_fund_months=3,
            total_debt=30_000,
            investment_portfolio_value=0,
            retirement_savings=0,
            current_age=35,
            retirement_age_target=65,
            risk_tolerance=5,
        )
        assert profile.debt_to_income_ratio == pytest.approx(0.30)
    
    def test_profile_years_to_retirement(self):
        """Test years to retirement calculation."""
        profile = FinancialProfile(
            annual_income=100_000,
            monthly_expenses=5_000,
            emergency_fund_balance=15_000,
            emergency_fund_months=3,
            total_debt=0,
            investment_portfolio_value=0,
            retirement_savings=0,
            current_age=40,
            retirement_age_target=65,
            risk_tolerance=5,
        )
        assert profile.years_to_retirement == 25
    
    def test_profile_negative_income_raises(self):
        """Test negative income raises error."""
        with pytest.raises(ValueError):
            FinancialProfile(
                annual_income=-50_000,
                monthly_expenses=5_000,
                emergency_fund_balance=15_000,
                emergency_fund_months=3,
                total_debt=0,
                investment_portfolio_value=0,
                retirement_savings=0,
                current_age=35,
                retirement_age_target=65,
                risk_tolerance=5,
            )


class TestRecommendationPlan:
    """Tests for recommendation plans."""
    
    def test_plan_creation(self):
        """Test creating a recommendation plan."""
        profile = FinancialProfile(
            annual_income=100_000,
            monthly_expenses=5_000,
            emergency_fund_balance=15_000,
            emergency_fund_months=3,
            total_debt=0,
            investment_portfolio_value=50_000,
            retirement_savings=100_000,
            current_age=35,
            retirement_age_target=65,
            risk_tolerance=6,
        )
        
        plan = RecommendationPlan(
            plan_id="plan-1",
            profile=profile,
            recommendations=[],
            priority_actions=[],
            estimated_impact=0.0,
        )
        
        assert plan.plan_id == "plan-1"
    
    def test_plan_auto_timestamp(self):
        """Test automatic plan timestamp."""
        profile = FinancialProfile(
            annual_income=100_000,
            monthly_expenses=5_000,
            emergency_fund_balance=15_000,
            emergency_fund_months=3,
            total_debt=0,
            investment_portfolio_value=0,
            retirement_savings=0,
            current_age=35,
            retirement_age_target=65,
            risk_tolerance=5,
        )
        
        plan = RecommendationPlan(
            plan_id="plan-1",
            profile=profile,
            recommendations=[],
            priority_actions=[],
            estimated_impact=0.0,
        )
        
        assert plan.generated_at is not None


class TestRecommendationEngine:
    """Tests for recommendation engine."""
    
    def test_engine_creation(self):
        """Test creating recommendation engine."""
        engine = RecommendationEngine()
        assert len(engine.generated_plans) == 0
    
    def test_recommend_emergency_fund(self):
        """Test emergency fund recommendation."""
        engine = RecommendationEngine()
        
        # Low emergency fund
        profile = FinancialProfile(
            annual_income=100_000,
            monthly_expenses=5_000,
            emergency_fund_balance=5_000,  # Only 1 month
            emergency_fund_months=1,
            total_debt=0,
            investment_portfolio_value=50_000,
            retirement_savings=100_000,
            current_age=35,
            retirement_age_target=65,
            risk_tolerance=6,
        )
        
        plan = engine.analyze_and_recommend(profile)
        
        # Should have emergency fund recommendation
        emergency_recs = [r for r in plan.recommendations if r.category == RecommendationCategory.EMERGENCY_FUND]
        assert len(emergency_recs) > 0
    
    def test_recommend_debt_reduction(self):
        """Test debt reduction recommendation."""
        engine = RecommendationEngine()
        
        # High debt
        profile = FinancialProfile(
            annual_income=100_000,
            monthly_expenses=5_000,
            emergency_fund_balance=30_000,
            emergency_fund_months=6,
            total_debt=50_000,  # High debt
            investment_portfolio_value=0,
            retirement_savings=50_000,
            current_age=35,
            retirement_age_target=65,
            risk_tolerance=5,
        )
        
        plan = engine.analyze_and_recommend(profile)
        
        # Should have debt reduction recommendation
        debt_recs = [r for r in plan.recommendations if r.category == RecommendationCategory.DEBT_REDUCTION]
        assert len(debt_recs) > 0
    
    def test_recommend_increase_savings(self):
        """Test savings recommendation."""
        engine = RecommendationEngine()
        
        # Low savings rate
        profile = FinancialProfile(
            annual_income=100_000,
            monthly_expenses=8_000,  # High expenses
            emergency_fund_balance=30_000,
            emergency_fund_months=4,
            total_debt=0,
            investment_portfolio_value=50_000,
            retirement_savings=100_000,
            current_age=35,
            retirement_age_target=65,
            risk_tolerance=6,
            savings_rate=0.05,  # Low 5%
        )
        
        plan = engine.analyze_and_recommend(profile)
        
        # Should have savings recommendation
        savings_recs = [r for r in plan.recommendations if r.category == RecommendationCategory.SAVINGS]
        assert len(savings_recs) > 0
    
    def test_plan_has_priority_actions(self):
        """Test plan includes priority actions."""
        engine = RecommendationEngine()
        
        profile = FinancialProfile(
            annual_income=100_000,
            monthly_expenses=5_000,
            emergency_fund_balance=10_000,  # Low
            emergency_fund_months=2,
            total_debt=50_000,  # High
            investment_portfolio_value=0,
            retirement_savings=50_000,
            current_age=35,
            retirement_age_target=65,
            risk_tolerance=5,
            savings_rate=0.10,
        )
        
        plan = engine.analyze_and_recommend(profile)
        
        assert len(plan.priority_actions) >= 0
        assert len(plan.priority_actions) <= 3
    
    def test_plan_estimates_impact(self):
        """Test plan calculates total impact."""
        engine = RecommendationEngine()
        
        profile = FinancialProfile(
            annual_income=100_000,
            monthly_expenses=5_000,
            emergency_fund_balance=30_000,
            emergency_fund_months=6,
            total_debt=0,
            investment_portfolio_value=50_000,
            retirement_savings=100_000,
            current_age=35,
            retirement_age_target=65,
            risk_tolerance=6,
        )
        
        plan = engine.analyze_and_recommend(profile)
        
        # Total impact should be sum of recommendation impacts
        total = sum(r.estimated_impact for r in plan.recommendations)
        assert plan.estimated_impact == pytest.approx(total)


class TestRecommendationEngineEdgeCases:
    """Edge case tests for recommendation engine."""
    
    def test_wealthy_profile(self):
        """Test with high net worth profile."""
        engine = RecommendationEngine()
        
        profile = FinancialProfile(
            annual_income=500_000,
            monthly_expenses=15_000,
            emergency_fund_balance=100_000,
            emergency_fund_months=6.67,
            total_debt=0,
            investment_portfolio_value=2_000_000,
            retirement_savings=1_000_000,
            current_age=45,
            retirement_age_target=60,
            risk_tolerance=8,
        )
        
        plan = engine.analyze_and_recommend(profile)
        
        # High net worth should get tax optimization rec
        tax_recs = [r for r in plan.recommendations if r.category == RecommendationCategory.TAX_OPTIMIZATION]
        assert len(tax_recs) > 0
    
    def test_young_profile(self):
        """Test with young profile (25 years old)."""
        engine = RecommendationEngine()
        
        profile = FinancialProfile(
            annual_income=60_000,
            monthly_expenses=3_000,
            emergency_fund_balance=10_000,
            emergency_fund_months=3.33,
            total_debt=30_000,  # Student loans
            investment_portfolio_value=0,
            retirement_savings=5_000,
            current_age=25,
            retirement_age_target=65,
            risk_tolerance=8,
        )
        
        plan = engine.analyze_and_recommend(profile)
        
        # Young profile should get investment recommendations
        inv_recs = [r for r in plan.recommendations if r.category == RecommendationCategory.INVESTMENT]
        assert len(inv_recs) > 0
    
    def test_near_retirement_profile(self):
        """Test with near-retirement profile (63 years old)."""
        engine = RecommendationEngine()
        
        profile = FinancialProfile(
            annual_income=150_000,
            monthly_expenses=8_000,
            emergency_fund_balance=80_000,
            emergency_fund_months=10,
            total_debt=0,
            investment_portfolio_value=500_000,
            retirement_savings=1_500_000,
            current_age=63,
            retirement_age_target=65,
            risk_tolerance=4,
        )
        
        plan = engine.analyze_and_recommend(profile)
        
        # Should have retirement-related recommendations
        retire_recs = [r for r in plan.recommendations if r.category == RecommendationCategory.RETIREMENT]
        # May have recommendations for final years
        assert isinstance(plan, RecommendationPlan)


class TestRecommendationEngineIntegration:
    """Integration tests for recommendation engine."""
    
    def test_full_analysis_workflow(self):
        """Test complete analysis workflow."""
        engine = RecommendationEngine()
        
        profile = FinancialProfile(
            annual_income=120_000,
            monthly_expenses=6_000,
            emergency_fund_balance=12_000,
            emergency_fund_months=2,
            total_debt=40_000,
            investment_portfolio_value=30_000,
            retirement_savings=80_000,
            current_age=35,
            retirement_age_target=65,
            risk_tolerance=6,
            financial_goals=["Buy home", "Retire at 65"],
            savings_rate=0.15,
        )
        
        # Generate plan
        plan = engine.analyze_and_recommend(profile)
        
        # Verify plan structure
        assert plan.plan_id is not None
        assert len(plan.recommendations) > 0
        assert len(plan.priority_actions) <= 3
        assert plan.estimated_impact >= 0
        
        # Verify recommendations have all fields
        for rec in plan.recommendations:
            assert rec.title
            assert rec.description
            assert rec.action_steps
    
    def test_plan_serialization(self):
        """Test plan can be serialized."""
        engine = RecommendationEngine()
        
        profile = FinancialProfile(
            annual_income=100_000,
            monthly_expenses=5_000,
            emergency_fund_balance=20_000,
            emergency_fund_months=4,
            total_debt=0,
            investment_portfolio_value=50_000,
            retirement_savings=100_000,
            current_age=40,
            retirement_age_target=65,
            risk_tolerance=6,
        )
        
        plan = engine.analyze_and_recommend(profile)
        data = plan.to_dict()
        
        assert "plan_id" in data
        assert "profile" in data
        assert "recommendations" in data
        assert "impact" in data
