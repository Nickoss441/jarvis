"""Tests for investment portfolio optimizer."""

import pytest
from datetime import datetime, timezone
import uuid

from jarvis.tools.portfolio_optimizer import (
    RiskTolerance, RebalancingStrategy, AssetAllocationTarget,
    PortfolioMetrics, RebalancingAction, RebalancingPlan, PortfolioOptimizer
)


class TestRiskTolerance:
    """Tests for risk tolerance enumeration."""
    
    def test_all_risk_levels_defined(self):
        """Verify all risk tolerance levels are defined."""
        levels = [r.value for r in RiskTolerance]
        assert "conservative" in levels
        assert "moderate" in levels
        assert "aggressive" in levels


class TestRebalancingStrategy:
    """Tests for rebalancing strategies."""
    
    def test_all_strategies_defined(self):
        """Verify all strategies are defined."""
        strategies = [s.value for s in RebalancingStrategy]
        assert "threshold" in strategies
        assert "periodic" in strategies
        assert "tactical" in strategies


class TestAssetAllocationTarget:
    """Tests for asset allocation targets."""
    
    def test_conservative_target(self):
        """Test conservative allocation target."""
        target = AssetAllocationTarget(
            name="Conservative",
            risk_tolerance=RiskTolerance.CONSERVATIVE,
            stocks_pct=30.0,
            bonds_pct=60.0,
            cash_pct=5.0,
            alternatives_pct=5.0,
            expected_return=4.5,
            expected_volatility=6.0,
        )
        assert target.stocks_pct == 30.0
        assert target.bonds_pct == 60.0
    
    def test_moderate_target(self):
        """Test moderate allocation target."""
        target = AssetAllocationTarget(
            name="Balanced",
            risk_tolerance=RiskTolerance.MODERATE,
            stocks_pct=60.0,
            bonds_pct=30.0,
            cash_pct=5.0,
            alternatives_pct=5.0,
            expected_return=6.5,
            expected_volatility=9.0,
        )
        assert target.stocks_pct == 60.0
    
    def test_aggressive_target(self):
        """Test aggressive allocation target."""
        target = AssetAllocationTarget(
            name="Aggressive",
            risk_tolerance=RiskTolerance.AGGRESSIVE,
            stocks_pct=80.0,
            bonds_pct=10.0,
            cash_pct=5.0,
            alternatives_pct=5.0,
            expected_return=8.5,
            expected_volatility=14.0,
        )
        assert target.stocks_pct == 80.0
    
    def test_allocation_not_summing_to_100_raises(self):
        """Test that allocations not summing to 100% raise error."""
        with pytest.raises(ValueError, match="must sum to 100%"):
            AssetAllocationTarget(
                name="Invalid",
                risk_tolerance=RiskTolerance.MODERATE,
                stocks_pct=50.0,
                bonds_pct=30.0,
                cash_pct=5.0,
                alternatives_pct=10.0,  # Total = 95%, should be ~100%
                expected_return=6.0,
                expected_volatility=9.0,
            )
    
    def test_target_to_dict(self):
        """Test allocation target serialization."""
        target = AssetAllocationTarget(
            name="Test",
            risk_tolerance=RiskTolerance.MODERATE,
            stocks_pct=60.0,
            bonds_pct=30.0,
            cash_pct=5.0,
            alternatives_pct=5.0,
            expected_return=6.5,
            expected_volatility=9.0,
        )
        data = target.to_dict()
        assert data["stocks"] == 60.0
        assert data["expected_return"] == 6.5


class TestPortfolioMetrics:
    """Tests for portfolio metrics."""
    
    def test_metrics_creation(self):
        """Test creating portfolio metrics."""
        metrics = PortfolioMetrics(
            total_value=500000.0,
            ytd_return=5.5,
            annualized_return=6.2,
            volatility=8.5,
            sharpe_ratio=0.65,
            diversification_score=85.0,
            largest_holding_pct=25.0,
            concentration_risk=25.0,
        )
        assert metrics.total_value == 500000.0
        assert metrics.sharpe_ratio == 0.65
    
    def test_metrics_to_dict(self):
        """Test metrics serialization."""
        metrics = PortfolioMetrics(
            total_value=250000.0,
            ytd_return=4.2,
            annualized_return=5.0,
            volatility=7.0,
            sharpe_ratio=0.50,
            diversification_score=80.0,
            largest_holding_pct=30.0,
            concentration_risk=30.0,
        )
        data = metrics.to_dict()
        assert data["total_value"] == 250000.0
        assert data["volatility"] == 7.0


class TestRebalancingAction:
    """Tests for rebalancing actions."""
    
    def test_buy_action(self):
        """Test creating a buy action."""
        action = RebalancingAction(
            asset_class="stocks",
            current_pct=50.0,
            target_pct=60.0,
            action="buy",
            amount=50000.0,
            rationale="Increase stock allocation",
        )
        assert action.action == "buy"
        assert action.amount == 50000.0
    
    def test_sell_action(self):
        """Test creating a sell action."""
        action = RebalancingAction(
            asset_class="bonds",
            current_pct=40.0,
            target_pct=30.0,
            action="sell",
            amount=50000.0,
            rationale="Reduce bond allocation",
        )
        assert action.action == "sell"
    
    def test_invalid_action_raises(self):
        """Test that invalid action raises error."""
        with pytest.raises(ValueError, match="'buy' or 'sell'"):
            RebalancingAction(
                asset_class="stocks",
                current_pct=50.0,
                target_pct=60.0,
                action="hold",
                amount=0.0,
                rationale="Test",
            )


class TestRebalancingPlan:
    """Tests for rebalancing plans."""
    
    def test_plan_creation(self):
        """Test creating a rebalancing plan."""
        ts = datetime.now(timezone.utc)
        plan = RebalancingPlan(
            plan_id=str(uuid.uuid4()),
            generated_at=ts,
            current_allocation={"stocks": 50.0, "bonds": 40.0, "cash": 10.0},
            target_allocation={"stocks": 60.0, "bonds": 30.0, "cash": 10.0},
            strategy=RebalancingStrategy.THRESHOLD,
            actions=[],
            total_trades_value=50000.0,
            estimated_tax_impact={},
            rebalancing_frequency="Quarterly",
            rationale="Rebalance to target allocation",
        )
        assert plan.strategy == RebalancingStrategy.THRESHOLD
    
    def test_plan_with_actions(self):
        """Test plan with rebalancing actions."""
        ts = datetime.now(timezone.utc)
        action = RebalancingAction(
            asset_class="stocks",
            current_pct=50.0,
            target_pct=60.0,
            action="buy",
            amount=50000.0,
            rationale="Increase stocks",
        )
        plan = RebalancingPlan(
            plan_id=str(uuid.uuid4()),
            generated_at=ts,
            current_allocation={"stocks": 50.0, "bonds": 50.0},
            target_allocation={"stocks": 60.0, "bonds": 40.0},
            strategy=RebalancingStrategy.THRESHOLD,
            actions=[action],
            total_trades_value=50000.0,
            estimated_tax_impact={},
            rebalancing_frequency="Quarterly",
            rationale="Rebalance",
        )
        assert len(plan.actions) == 1
    
    def test_plan_naive_datetime_raises(self):
        """Test that naive datetime raises error."""
        ts = datetime(2026, 4, 27, 10, 0, 0)  # No timezone
        with pytest.raises(ValueError, match="timezone-aware"):
            RebalancingPlan(
                plan_id=str(uuid.uuid4()),
                generated_at=ts,
                current_allocation={},
                target_allocation={},
                strategy=RebalancingStrategy.THRESHOLD,
                actions=[],
                total_trades_value=0.0,
                estimated_tax_impact={},
                rebalancing_frequency="Quarterly",
                rationale="Test",
            )
    
    def test_plan_to_dict(self):
        """Test plan serialization."""
        ts = datetime.now(timezone.utc)
        plan = RebalancingPlan(
            plan_id="plan-123",
            generated_at=ts,
            current_allocation={"stocks": 55.0, "bonds": 45.0},
            target_allocation={"stocks": 60.0, "bonds": 40.0},
            strategy=RebalancingStrategy.PERIODIC,
            actions=[],
            total_trades_value=25000.0,
            estimated_tax_impact={},
            rebalancing_frequency="Quarterly",
            rationale="Rebalance",
        )
        data = plan.to_dict()
        assert data["plan_id"] == "plan-123"
        assert data["strategy"] == "periodic"


class TestPortfolioOptimizer:
    """Tests for portfolio optimizer."""
    
    def test_optimizer_creation(self):
        """Test creating optimizer."""
        optimizer = PortfolioOptimizer()
        assert optimizer.risk_free_rate == 3.0
    
    def test_get_conservative_target(self):
        """Test getting conservative allocation."""
        optimizer = PortfolioOptimizer()
        target = optimizer.get_target_allocation(RiskTolerance.CONSERVATIVE)
        assert target.stocks_pct == 30.0
        assert target.bonds_pct == 60.0
    
    def test_get_moderate_target(self):
        """Test getting moderate allocation."""
        optimizer = PortfolioOptimizer()
        target = optimizer.get_target_allocation(RiskTolerance.MODERATE)
        assert target.stocks_pct == 60.0
        assert target.bonds_pct == 30.0
    
    def test_get_aggressive_target(self):
        """Test getting aggressive allocation."""
        optimizer = PortfolioOptimizer()
        target = optimizer.get_target_allocation(RiskTolerance.AGGRESSIVE)
        assert target.stocks_pct == 80.0
        assert target.bonds_pct == 10.0
    
    def test_calculate_metrics(self):
        """Test calculating portfolio metrics."""
        optimizer = PortfolioOptimizer()
        metrics = optimizer.calculate_portfolio_metrics(
            total_value=500000.0,
            current_allocation={"stocks": 60.0, "bonds": 30.0, "cash": 10.0},
            returns={"stocks": 8.0, "bonds": 3.0, "cash": 1.0},
            volatilities={"stocks": 15.0, "bonds": 4.0, "cash": 0.5},
        )
        assert metrics.total_value == 500000.0
        assert metrics.ytd_return > 0
    
    def test_metrics_with_concentration(self):
        """Test metrics with concentrated portfolio."""
        optimizer = PortfolioOptimizer()
        metrics = optimizer.calculate_portfolio_metrics(
            total_value=100000.0,
            current_allocation={"stocks": 80.0, "bonds": 20.0},
            returns={"stocks": 10.0, "bonds": 2.0},
            volatilities={"stocks": 12.0, "bonds": 3.0},
        )
        assert metrics.largest_holding_pct == 80.0
        assert metrics.concentration_risk == 80.0
        assert metrics.diversification_score < 100
    
    def test_generate_rebalancing_plan(self):
        """Test generating rebalancing plan."""
        optimizer = PortfolioOptimizer()
        plan = optimizer.generate_rebalancing_plan(
            total_value=500000.0,
            current_allocation={"stocks": 50.0, "bonds": 40.0, "cash": 10.0},
            risk_tolerance=RiskTolerance.MODERATE,
            strategy=RebalancingStrategy.THRESHOLD,
            threshold_pct=5.0,
        )
        assert plan.total_trades_value >= 0
        assert len(plan.actions) >= 0
    
    def test_rebalancing_with_large_drift(self):
        """Test rebalancing when allocation drifts significantly."""
        optimizer = PortfolioOptimizer()
        plan = optimizer.generate_rebalancing_plan(
            total_value=500000.0,
            current_allocation={"stocks": 30.0, "bonds": 60.0, "cash": 10.0},
            risk_tolerance=RiskTolerance.MODERATE,  # Target: 60% stocks, 30% bonds
            strategy=RebalancingStrategy.THRESHOLD,
            threshold_pct=5.0,
        )
        # Should generate actions since drift > 5%
        assert len(plan.actions) > 0
    
    def test_analyze_diversification_concentrated(self):
        """Test diversification analysis of concentrated portfolio."""
        optimizer = PortfolioOptimizer()
        analysis = optimizer.analyze_diversification({
            "stocks": 70.0,
            "bonds": 20.0,
            "cash": 10.0,
        })
        assert analysis["concentration_ratio"] == 70.0
        assert analysis["num_asset_classes"] == 3
        assert len(analysis["recommendations"]) > 0
    
    def test_analyze_diversification_wellbalanced(self):
        """Test diversification analysis of well-balanced portfolio."""
        optimizer = PortfolioOptimizer()
        analysis = optimizer.analyze_diversification({
            "stocks": 35.0,
            "bonds": 30.0,
            "cash": 20.0,
            "alternatives": 15.0,
        })
        assert analysis["num_asset_classes"] == 4
        assert analysis["score"] > 50  # Well-balanced gets reasonable score
    
    def test_analyze_diversification_underdiversified(self):
        """Test diversification analysis of underdiversified portfolio."""
        optimizer = PortfolioOptimizer()
        analysis = optimizer.analyze_diversification({
            "stocks": 100.0,
        })
        assert analysis["num_asset_classes"] == 1
        assert len(analysis["recommendations"]) > 0
    
    def test_calculate_correlation_matrix(self):
        """Test calculating correlation matrix."""
        optimizer = PortfolioOptimizer()
        correlations = optimizer.calculate_correlation_matrix({
            "stocks": [10.0, 5.0, 8.0, 12.0],
            "bonds": [2.0, 3.0, 1.0, 4.0],
        })
        assert ("stocks", "stocks") in correlations
        assert ("bonds", "bonds") in correlations
        assert ("stocks", "bonds") in correlations
        # Self-correlation should be 1.0
        assert correlations[("stocks", "stocks")] == 1.0
    
    def test_correlation_between_assets(self):
        """Test correlation calculation between assets."""
        optimizer = PortfolioOptimizer()
        correlations = optimizer.calculate_correlation_matrix({
            "asset_a": [1.0, 2.0, 3.0, 4.0],
            "asset_b": [2.0, 4.0, 6.0, 8.0],  # Perfectly correlated with asset_a
        })
        # Should be close to 1.0 (perfect positive correlation)
        assert correlations[("asset_a", "asset_b")] > 0.99


class TestPortfolioOptimizerEdgeCases:
    """Edge case tests for portfolio optimizer."""
    
    def test_metrics_with_zero_volatility(self):
        """Test metrics calculation with zero volatility."""
        optimizer = PortfolioOptimizer()
        metrics = optimizer.calculate_portfolio_metrics(
            total_value=100000.0,
            current_allocation={"cash": 100.0},
            returns={"cash": 1.0},
            volatilities={"cash": 0.0},
        )
        assert metrics.volatility == 0.0
        assert metrics.sharpe_ratio == 0.0
    
    def test_empty_allocation(self):
        """Test with empty allocation."""
        optimizer = PortfolioOptimizer()
        analysis = optimizer.analyze_diversification({})
        assert analysis["score"] == 0
    
    def test_single_asset_allocation(self):
        """Test with single asset allocation."""
        optimizer = PortfolioOptimizer()
        analysis = optimizer.analyze_diversification({"stocks": 100.0})
        assert analysis["num_asset_classes"] == 1
        assert analysis["concentration_ratio"] == 100.0
    
    def test_rebalancing_at_target(self):
        """Test rebalancing when already at target."""
        optimizer = PortfolioOptimizer()
        plan = optimizer.generate_rebalancing_plan(
            total_value=100000.0,
            current_allocation={"stocks": 60.0, "bonds": 30.0, "cash": 5.0, "alternatives": 5.0},
            risk_tolerance=RiskTolerance.MODERATE,  # Exact match
            threshold_pct=5.0,
        )
        # No rebalancing needed
        assert len(plan.actions) == 0
        assert plan.total_trades_value == 0.0
