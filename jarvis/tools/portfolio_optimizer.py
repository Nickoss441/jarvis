"""Investment portfolio optimizer.

Provides portfolio rebalancing recommendations, modern portfolio theory
analysis, and asset allocation optimization strategies.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
import statistics
import uuid


class RiskTolerance(str, Enum):
    """Risk tolerance levels."""
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"


class RebalancingStrategy(str, Enum):
    """Portfolio rebalancing strategies."""
    THRESHOLD = "threshold"  # Rebalance when allocation drifts by threshold %
    PERIODIC = "periodic"     # Rebalance at fixed intervals
    TACTICAL = "tactical"     # Rebalance based on market conditions


@dataclass
class AssetAllocationTarget:
    """Target asset allocation for portfolio.
    
    Attributes:
        name: Allocation profile name (e.g., "Conservative Growth")
        risk_tolerance: Risk tolerance level
        stocks_pct: Target stock allocation percentage
        bonds_pct: Target bond allocation percentage
        cash_pct: Target cash allocation percentage
        alternatives_pct: Target alternative assets percentage
        expected_return: Expected annual return percentage
        expected_volatility: Expected annual volatility percentage
    """
    name: str
    risk_tolerance: RiskTolerance
    stocks_pct: float
    bonds_pct: float
    cash_pct: float
    alternatives_pct: float
    expected_return: float
    expected_volatility: float
    
    def __post_init__(self):
        """Validate allocation."""
        total = self.stocks_pct + self.bonds_pct + self.cash_pct + self.alternatives_pct
        if not (99.0 <= total <= 101.0):  # Allow 1% rounding error
            raise ValueError(f"Allocations must sum to 100%, got {total}%")
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "risk_tolerance": self.risk_tolerance.value,
            "stocks": self.stocks_pct,
            "bonds": self.bonds_pct,
            "cash": self.cash_pct,
            "alternatives": self.alternatives_pct,
            "expected_return": self.expected_return,
            "expected_volatility": self.expected_volatility,
        }


@dataclass
class PortfolioMetrics:
    """Key portfolio performance metrics.
    
    Attributes:
        total_value: Total portfolio value
        ytd_return: Year-to-date return percentage
        annualized_return: Annualized return percentage
        volatility: Portfolio volatility (standard deviation)
        sharpe_ratio: Risk-adjusted return metric
        diversification_score: Score from 0-100 measuring diversification
        largest_holding_pct: Percentage of largest single holding
        concentration_risk: Risk score from concentration (0-100)
    """
    total_value: float
    ytd_return: float
    annualized_return: float
    volatility: float
    sharpe_ratio: float
    diversification_score: float
    largest_holding_pct: float
    concentration_risk: float
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "total_value": self.total_value,
            "ytd_return": self.ytd_return,
            "annualized_return": self.annualized_return,
            "volatility": self.volatility,
            "sharpe_ratio": self.sharpe_ratio,
            "diversification_score": self.diversification_score,
            "largest_holding_pct": self.largest_holding_pct,
            "concentration_risk": self.concentration_risk,
        }


@dataclass
class RebalancingAction:
    """Single rebalancing action for portfolio.
    
    Attributes:
        asset_class: Asset class to adjust (stocks, bonds, cash, alternatives)
        current_pct: Current allocation percentage
        target_pct: Target allocation percentage
        action: "buy" or "sell"
        amount: Dollar amount to trade
        rationale: Explanation for action
    """
    asset_class: str
    current_pct: float
    target_pct: float
    action: str
    amount: float
    rationale: str
    
    def __post_init__(self):
        """Validate action."""
        if self.action not in ["buy", "sell"]:
            raise ValueError("action must be 'buy' or 'sell'")


@dataclass
class RebalancingPlan:
    """Comprehensive portfolio rebalancing plan.
    
    Attributes:
        plan_id: Unique plan identifier
        generated_at: When plan was generated (UTC)
        current_allocation: Current asset allocation percentages
        target_allocation: Target asset allocation percentages
        strategy: Rebalancing strategy to use
        actions: List of rebalancing actions
        total_trades_value: Total value of trades needed
        estimated_tax_impact: Estimated tax implications
        rebalancing_frequency: Recommended rebalancing frequency
        rationale: Explanation of the plan
    """
    plan_id: str
    generated_at: datetime
    current_allocation: dict[str, float]
    target_allocation: dict[str, float]
    strategy: RebalancingStrategy
    actions: list[RebalancingAction]
    total_trades_value: float
    estimated_tax_impact: dict[str, float]
    rebalancing_frequency: str
    rationale: str
    
    def __post_init__(self):
        """Validate plan."""
        if not isinstance(self.generated_at, datetime):
            raise ValueError("generated_at must be a datetime object")
        if self.generated_at.tzinfo is None:
            raise ValueError("generated_at must be timezone-aware (UTC)")
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "plan_id": self.plan_id,
            "generated_at": self.generated_at.isoformat(),
            "current": self.current_allocation,
            "target": self.target_allocation,
            "strategy": self.strategy.value,
            "actions": [
                {
                    "asset": a.asset_class,
                    "current": a.current_pct,
                    "target": a.target_pct,
                    "action": a.action,
                    "amount": a.amount,
                    "rationale": a.rationale,
                }
                for a in self.actions
            ],
            "total_trades": self.total_trades_value,
            "tax_impact": self.estimated_tax_impact,
            "frequency": self.rebalancing_frequency,
            "rationale": self.rationale,
        }


class PortfolioOptimizer:
    """Optimizer for investment portfolio asset allocation."""
    
    # Standard allocation targets by risk tolerance
    ALLOCATION_TARGETS = {
        RiskTolerance.CONSERVATIVE: AssetAllocationTarget(
            name="Conservative Growth",
            risk_tolerance=RiskTolerance.CONSERVATIVE,
            stocks_pct=30.0,
            bonds_pct=60.0,
            cash_pct=5.0,
            alternatives_pct=5.0,
            expected_return=4.5,
            expected_volatility=6.0,
        ),
        RiskTolerance.MODERATE: AssetAllocationTarget(
            name="Balanced Growth",
            risk_tolerance=RiskTolerance.MODERATE,
            stocks_pct=60.0,
            bonds_pct=30.0,
            cash_pct=5.0,
            alternatives_pct=5.0,
            expected_return=6.5,
            expected_volatility=9.0,
        ),
        RiskTolerance.AGGRESSIVE: AssetAllocationTarget(
            name="Aggressive Growth",
            risk_tolerance=RiskTolerance.AGGRESSIVE,
            stocks_pct=80.0,
            bonds_pct=10.0,
            cash_pct=5.0,
            alternatives_pct=5.0,
            expected_return=8.5,
            expected_volatility=14.0,
        ),
    }
    
    def __init__(self):
        """Initialize portfolio optimizer."""
        self.risk_free_rate = 3.0  # Assume 3% risk-free rate
    
    def get_target_allocation(self, risk_tolerance: RiskTolerance) -> AssetAllocationTarget:
        """Get standard allocation target for risk tolerance level.
        
        Args:
            risk_tolerance: Risk tolerance level
        
        Returns:
            AssetAllocationTarget for the risk level
        """
        return self.ALLOCATION_TARGETS[risk_tolerance]
    
    def calculate_portfolio_metrics(
        self,
        total_value: float,
        current_allocation: dict[str, float],
        returns: dict[str, float],
        volatilities: dict[str, float],
    ) -> PortfolioMetrics:
        """Calculate portfolio performance metrics.
        
        Args:
            total_value: Total portfolio value
            current_allocation: Dict of asset_class -> percentage
            returns: Dict of asset_class -> return percentage
            volatilities: Dict of asset_class -> volatility percentage
        
        Returns:
            PortfolioMetrics with calculated values
        """
        # Calculate weighted portfolio return
        portfolio_return = sum(
            current_allocation.get(asset, 0) * returns.get(asset, 0) / 100
            for asset in returns.keys()
        )
        
        # Calculate weighted portfolio volatility (simplified, assumes no correlation)
        portfolio_volatility = (
            sum(
                (current_allocation.get(asset, 0) / 100) ** 2 * (volatilities.get(asset, 0)) ** 2
                for asset in volatilities.keys()
            ) ** 0.5
        )
        
        # Calculate Sharpe ratio
        sharpe_ratio = (portfolio_return - self.risk_free_rate / 100) / (portfolio_volatility / 100) if portfolio_volatility > 0 else 0
        
        # Calculate diversification score (0-100)
        # More concentrated = lower score
        largest_holding = max(current_allocation.values()) if current_allocation else 0
        diversification_score = min(100, (100 - largest_holding))
        
        # Concentration risk (inverse of diversification)
        concentration_risk = largest_holding
        
        return PortfolioMetrics(
            total_value=total_value,
            ytd_return=portfolio_return * 100,
            annualized_return=portfolio_return * 100,
            volatility=portfolio_volatility,
            sharpe_ratio=sharpe_ratio,
            diversification_score=diversification_score,
            largest_holding_pct=largest_holding,
            concentration_risk=concentration_risk,
        )
    
    def generate_rebalancing_plan(
        self,
        total_value: float,
        current_allocation: dict[str, float],
        risk_tolerance: RiskTolerance,
        strategy: RebalancingStrategy = RebalancingStrategy.THRESHOLD,
        threshold_pct: float = 5.0,
    ) -> RebalancingPlan:
        """Generate portfolio rebalancing plan.
        
        Args:
            total_value: Total portfolio value
            current_allocation: Dict of asset_class -> percentage
            risk_tolerance: Risk tolerance level
            strategy: Rebalancing strategy to use
            threshold_pct: Drift threshold for threshold-based rebalancing
        
        Returns:
            RebalancingPlan with actions and analysis
        """
        target = self.get_target_allocation(risk_tolerance)
        target_dict = {
            "stocks": target.stocks_pct,
            "bonds": target.bonds_pct,
            "cash": target.cash_pct,
            "alternatives": target.alternatives_pct,
        }
        
        actions: list[RebalancingAction] = []
        total_trades = 0.0
        
        # Determine which assets need rebalancing
        for asset_class, target_pct in target_dict.items():
            current_pct = current_allocation.get(asset_class, 0.0)
            drift = abs(current_pct - target_pct)
            
            # Only create actions if drift exceeds threshold
            if drift >= threshold_pct:
                current_value = (current_pct / 100) * total_value
                target_value = (target_pct / 100) * total_value
                diff_value = target_value - current_value
                
                action = "buy" if diff_value > 0 else "sell"
                amount = abs(diff_value)
                
                rationale = (
                    f"{asset_class.title()} is {diff_value/target_value*100:.1f}% "
                    f"from target allocation of {target_pct:.0f}%"
                )
                
                actions.append(RebalancingAction(
                    asset_class=asset_class,
                    current_pct=current_pct,
                    target_pct=target_pct,
                    action=action,
                    amount=amount,
                    rationale=rationale,
                ))
                
                total_trades += amount
        
        # Estimate tax impact (simplified)
        tax_impact = {
            "estimated_short_term_gains": total_trades * 0.15,
            "estimated_long_term_gains": 0.0,
            "wash_sale_risk": "low" if total_trades < total_value * 0.1 else "medium",
        }
        
        # Determine rebalancing frequency
        if strategy == RebalancingStrategy.PERIODIC:
            frequency = "Quarterly"
        elif strategy == RebalancingStrategy.THRESHOLD:
            frequency = f"When allocation drifts {threshold_pct}%+ from target"
        else:
            frequency = "Based on market conditions"
        
        return RebalancingPlan(
            plan_id=str(uuid.uuid4()),
            generated_at=datetime.now(timezone.utc),
            current_allocation=current_allocation,
            target_allocation=target_dict,
            strategy=strategy,
            actions=actions,
            total_trades_value=total_trades,
            estimated_tax_impact=tax_impact,
            rebalancing_frequency=frequency,
            rationale=(
                f"Rebalancing to {risk_tolerance.value} portfolio targeting "
                f"{target.stocks_pct:.0f}% stocks, {target.bonds_pct:.0f}% bonds, "
                f"{target.cash_pct:.0f}% cash, {target.alternatives_pct:.0f}% alternatives"
            ),
        )
    
    def analyze_diversification(self, current_allocation: dict[str, float]) -> dict:
        """Analyze portfolio diversification.
        
        Args:
            current_allocation: Dict of asset_class -> percentage
        
        Returns:
            Dict with diversification analysis
        """
        if not current_allocation:
            return {"analysis": "No holdings", "score": 0, "recommendations": []}
        
        allocations = list(current_allocation.values())
        max_allocation = max(allocations)
        
        # Calculate Herfindahl Index (concentration measure)
        herfindahl = sum(pct ** 2 for pct in allocations) / 10000
        
        # Diversification score (0-100, higher is better)
        num_assets = len(current_allocation)
        diversification_score = min(100, num_assets * 20 * (1 - herfindahl))
        
        recommendations = []
        if max_allocation > 50:
            recommendations.append(f"Reduce concentration: largest holding is {max_allocation:.0f}%")
        if num_assets < 4:
            recommendations.append(f"Increase diversification: only {num_assets} asset classes")
        if herfindahl > 0.25:
            recommendations.append("Portfolio is highly concentrated - increase diversification")
        
        return {
            "score": diversification_score,
            "herfindahl_index": herfindahl,
            "concentration_ratio": max_allocation,
            "num_asset_classes": num_assets,
            "recommendations": recommendations,
        }
    
    def calculate_correlation_matrix(
        self,
        returns_data: dict[str, list[float]],
    ) -> dict[tuple, float]:
        """Calculate correlations between asset class returns.
        
        Args:
            returns_data: Dict of asset_class -> list of return values
        
        Returns:
            Dict of (asset1, asset2) -> correlation coefficient
        """
        correlations = {}
        assets = list(returns_data.keys())
        
        for i, asset1 in enumerate(assets):
            for asset2 in assets[i:]:
                if asset1 == asset2:
                    correlations[(asset1, asset2)] = 1.0
                else:
                    returns1 = returns_data[asset1]
                    returns2 = returns_data[asset2]
                    
                    if len(returns1) > 1 and len(returns2) > 1:
                        mean1 = statistics.mean(returns1)
                        mean2 = statistics.mean(returns2)
                        
                        covariance = sum(
                            (r1 - mean1) * (r2 - mean2)
                            for r1, r2 in zip(returns1, returns2)
                        ) / (len(returns1) - 1)
                        
                        std1 = statistics.stdev(returns1)
                        std2 = statistics.stdev(returns2)
                        
                        correlation = covariance / (std1 * std2) if std1 * std2 > 0 else 0
                        correlations[(asset1, asset2)] = correlation
                    else:
                        correlations[(asset1, asset2)] = 0.0
        
        return correlations
