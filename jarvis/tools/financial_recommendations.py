"""Financial recommendations engine for personalized advice.

Analyzes financial situation across all dimensions (income, spending,
savings, investments, debt, goals) and generates personalized recommendations.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Any
import uuid


class RecommendationCategory(str, Enum):
    """Categories of financial recommendations."""
    EMERGENCY_FUND = "emergency_fund"
    DEBT_REDUCTION = "debt_reduction"
    SAVINGS = "savings"
    INVESTMENT = "investment"
    TAX_OPTIMIZATION = "tax_optimization"
    SPENDING = "spending"
    INSURANCE = "insurance"
    RETIREMENT = "retirement"
    EDUCATION = "education"
    GOAL_PLANNING = "goal_planning"


class RecommendationPriority(str, Enum):
    """Priority levels for recommendations."""
    CRITICAL = "critical"      # Immediate action required
    HIGH = "high"              # Important, address soon
    MEDIUM = "medium"          # Beneficial, plan to implement
    LOW = "low"                # Nice to have


class RecommendationStatus(str, Enum):
    """Status of recommendation implementation."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    DISMISSED = "dismissed"


@dataclass
class Recommendation:
    """Individual financial recommendation.
    
    Attributes:
        recommendation_id: Unique ID
        category: Recommendation category
        title: Short title
        description: Detailed description
        rationale: Why this is recommended
        target_metric: What metric this addresses
        current_value: Current metric value
        target_value: Target metric value
        priority: Implementation priority
        estimated_impact: Estimated financial impact
        estimated_timeframe: Timeframe to realize benefit (months)
        action_steps: Specific steps to implement
        status: Implementation status
        created_at: When recommendation was generated
    """
    recommendation_id: str
    category: RecommendationCategory
    title: str
    description: str
    rationale: str
    target_metric: str
    current_value: Any
    target_value: Any
    priority: RecommendationPriority
    estimated_impact: float
    estimated_timeframe: int
    action_steps: list[str]
    status: RecommendationStatus = RecommendationStatus.NOT_STARTED
    created_at: datetime = None
    
    def __post_init__(self):
        """Set defaults."""
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.recommendation_id,
            "category": self.category.value,
            "title": self.title,
            "description": self.description,
            "rationale": self.rationale,
            "metric": self.target_metric,
            "current": str(self.current_value),
            "target": str(self.target_value),
            "priority": self.priority.value,
            "impact": self.estimated_impact,
            "timeframe": self.estimated_timeframe,
            "steps": self.action_steps,
            "status": self.status.value,
        }


@dataclass
class FinancialProfile:
    """User's financial profile for analysis.
    
    Attributes:
        annual_income: Annual income
        monthly_expenses: Average monthly spending
        emergency_fund_balance: Current emergency fund
        emergency_fund_months: Target emergency fund (months of expenses)
        total_debt: Total debt outstanding
        investment_portfolio_value: Total investment value
        retirement_savings: Retirement account balance
        current_age: Current age
        retirement_age_target: Target retirement age
        risk_tolerance: Investment risk tolerance (1-10)
        financial_goals: List of financial goals
        savings_rate: Current savings rate percentage
    """
    annual_income: float
    monthly_expenses: float
    emergency_fund_balance: float
    emergency_fund_months: float
    total_debt: float
    investment_portfolio_value: float
    retirement_savings: float
    current_age: int
    retirement_age_target: int
    risk_tolerance: int
    financial_goals: list[str] = field(default_factory=list)
    savings_rate: float = 0.0
    
    def __post_init__(self):
        """Validate profile."""
        if self.annual_income < 0:
            raise ValueError("Income cannot be negative")
        if self.current_age < 0:
            raise ValueError("Age cannot be negative")
    
    @property
    def monthly_income(self) -> float:
        """Calculate monthly income."""
        return self.annual_income / 12
    
    @property
    def net_worth(self) -> float:
        """Calculate net worth."""
        return (self.emergency_fund_balance + self.investment_portfolio_value +
                self.retirement_savings - self.total_debt)
    
    @property
    def debt_to_income_ratio(self) -> float:
        """Calculate debt-to-income ratio."""
        if self.annual_income == 0:
            return 0
        return self.total_debt / self.annual_income
    
    @property
    def years_to_retirement(self) -> int:
        """Calculate years until retirement."""
        return self.retirement_age_target - self.current_age
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "income": self.annual_income,
            "expenses": self.monthly_expenses,
            "emergency_fund": self.emergency_fund_balance,
            "debt": self.total_debt,
            "investments": self.investment_portfolio_value,
            "retirement": self.retirement_savings,
            "net_worth": self.net_worth,
            "debt_to_income": self.debt_to_income_ratio,
            "age": self.current_age,
            "years_to_retirement": self.years_to_retirement,
        }


@dataclass
class RecommendationPlan:
    """Comprehensive financial recommendation plan.
    
    Attributes:
        plan_id: Unique plan ID
        profile: Financial profile analyzed
        recommendations: List of recommendations
        priority_actions: Top 3 immediate actions
        estimated_impact: Total estimated financial impact
        generated_at: When plan was generated
    """
    plan_id: str
    profile: FinancialProfile
    recommendations: list[Recommendation]
    priority_actions: list[str]
    estimated_impact: float
    generated_at: datetime = None
    
    def __post_init__(self):
        """Set defaults."""
        if self.generated_at is None:
            self.generated_at = datetime.now(timezone.utc)
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "plan_id": self.plan_id,
            "profile": self.profile.to_dict(),
            "recommendations": [r.to_dict() for r in self.recommendations],
            "priority_actions": self.priority_actions,
            "impact": self.estimated_impact,
            "generated": self.generated_at.isoformat(),
        }


class RecommendationEngine:
    """Financial recommendations engine."""
    
    # Industry benchmarks
    EMERGENCY_FUND_MONTHS = 6
    MAX_DEBT_TO_INCOME = 0.36
    RECOMMENDED_SAVINGS_RATE = 0.20
    RECOMMENDED_RETIREMENT_SAVINGS_PER_YEAR = 23_500  # 2024 limit
    
    def __init__(self):
        """Initialize recommendation engine."""
        self.generated_plans: dict[str, RecommendationPlan] = {}
    
    def analyze_and_recommend(self, profile: FinancialProfile) -> RecommendationPlan:
        """Analyze financial profile and generate recommendations.
        
        Args:
            profile: Financial profile to analyze
        
        Returns:
            Recommendation plan with personalized advice
        """
        recommendations = []
        
        # Emergency fund analysis
        if profile.emergency_fund_balance < profile.monthly_expenses * self.EMERGENCY_FUND_MONTHS:
            recommendations.append(self._recommend_emergency_fund(profile))
        
        # Debt analysis
        if profile.debt_to_income_ratio > self.MAX_DEBT_TO_INCOME:
            recommendations.append(self._recommend_debt_reduction(profile))
        
        # Savings analysis
        if profile.savings_rate < self.RECOMMENDED_SAVINGS_RATE:
            recommendations.append(self._recommend_increase_savings(profile))
        
        # Investment analysis
        if profile.investment_portfolio_value == 0 and profile.annual_income > 50_000:
            recommendations.append(self._recommend_start_investing(profile))
        
        # Retirement analysis
        years_left = profile.years_to_retirement
        if years_left > 0:
            target_retirement = profile.annual_income * 25  # 4% rule
            if profile.retirement_savings < target_retirement * 0.5:
                recommendations.append(self._recommend_increase_retirement_savings(profile))
        
        # Tax optimization
        if profile.investment_portfolio_value > 100_000:
            recommendations.append(self._recommend_tax_optimization(profile))
        
        # Spending analysis
        if profile.monthly_expenses > profile.monthly_income * 0.6:
            recommendations.append(self._recommend_spending_reduction(profile))
        
        # Insurance analysis
        if profile.net_worth > 250_000:
            recommendations.append(self._recommend_umbrella_insurance(profile))
        
        # Goal planning
        if not profile.financial_goals:
            recommendations.append(self._recommend_goal_setting(profile))
        
        # Sort by priority
        recommendations.sort(key=lambda r: self._priority_value(r.priority), reverse=True)
        
        # Identify priority actions (top 3 highest impact, highest priority)
        priority_actions = [
            r.action_steps[0] if r.action_steps else r.title
            for r in recommendations[:3]
        ]
        
        # Calculate total impact
        total_impact = sum(r.estimated_impact for r in recommendations)
        
        plan = RecommendationPlan(
            plan_id=str(uuid.uuid4()),
            profile=profile,
            recommendations=recommendations,
            priority_actions=priority_actions,
            estimated_impact=total_impact,
        )
        
        self.generated_plans[plan.plan_id] = plan
        return plan
    
    def _priority_value(self, priority: RecommendationPriority) -> int:
        """Convert priority to numeric value."""
        values = {
            RecommendationPriority.CRITICAL: 4,
            RecommendationPriority.HIGH: 3,
            RecommendationPriority.MEDIUM: 2,
            RecommendationPriority.LOW: 1,
        }
        return values.get(priority, 0)
    
    def _recommend_emergency_fund(self, profile: FinancialProfile) -> Recommendation:
        """Recommend building emergency fund."""
        target = profile.monthly_expenses * self.EMERGENCY_FUND_MONTHS
        shortage = target - profile.emergency_fund_balance
        
        return Recommendation(
            recommendation_id=str(uuid.uuid4()),
            category=RecommendationCategory.EMERGENCY_FUND,
            title="Build Emergency Fund",
            description="Establish or expand emergency savings to cover 6 months of expenses",
            rationale="Emergency fund provides financial security and prevents debt accumulation from unexpected expenses",
            target_metric="Emergency Fund",
            current_value=f"${profile.emergency_fund_balance:,.0f}",
            target_value=f"${target:,.0f}",
            priority=RecommendationPriority.CRITICAL,
            estimated_impact=0.0,  # Protective, not income-generating
            estimated_timeframe=24,
            action_steps=[
                f"Open high-yield savings account",
                f"Automate monthly savings of ${shortage / 24:,.0f}",
                "Keep funds liquid and accessible",
            ],
        )
    
    def _recommend_debt_reduction(self, profile: FinancialProfile) -> Recommendation:
        """Recommend reducing debt."""
        monthly_payment = profile.total_debt / 24  # 2-year payoff plan
        monthly_interest_saved = profile.total_debt * 0.05 / 12  # Average 5% rate
        annual_impact = monthly_interest_saved * 12
        
        return Recommendation(
            recommendation_id=str(uuid.uuid4()),
            category=RecommendationCategory.DEBT_REDUCTION,
            title="Prioritize Debt Reduction",
            description=f"Reduce debt from ${profile.total_debt:,.0f} to zero",
            rationale="High debt-to-income ratio restricts financial flexibility and costs money in interest",
            target_metric="Debt-to-Income Ratio",
            current_value=f"{profile.debt_to_income_ratio:.1%}",
            target_value="< 36%",
            priority=RecommendationPriority.HIGH,
            estimated_impact=annual_impact,
            estimated_timeframe=24,
            action_steps=[
                f"Budget ${monthly_payment:,.0f} monthly for debt repayment",
                "Consider avalanche method (highest interest first)",
                "Negotiate lower rates with creditors",
            ],
        )
    
    def _recommend_increase_savings(self, profile: FinancialProfile) -> Recommendation:
        """Recommend increasing savings rate."""
        target_monthly = profile.monthly_income * self.RECOMMENDED_SAVINGS_RATE
        current_monthly = profile.monthly_income * profile.savings_rate
        increase_needed = target_monthly - current_monthly
        annual_impact = increase_needed * 12
        
        return Recommendation(
            recommendation_id=str(uuid.uuid4()),
            category=RecommendationCategory.SAVINGS,
            title="Increase Savings Rate",
            description="Build up savings to 20% of gross income",
            rationale="Higher savings rate accelerates wealth building and financial independence",
            target_metric="Savings Rate",
            current_value=f"{profile.savings_rate:.0%}",
            target_value="20%",
            priority=RecommendationPriority.HIGH,
            estimated_impact=annual_impact,
            estimated_timeframe=12,
            action_steps=[
                f"Increase automatic transfers to ${target_monthly:,.0f}/month",
                "Review and reduce discretionary spending",
                "Automate savings before spending money",
            ],
        )
    
    def _recommend_start_investing(self, profile: FinancialProfile) -> Recommendation:
        """Recommend starting investment portfolio."""
        annual_investment = profile.monthly_income * 0.10  # 10% of income
        expected_return = annual_investment * 0.07  # 7% average annual return
        
        return Recommendation(
            recommendation_id=str(uuid.uuid4()),
            category=RecommendationCategory.INVESTMENT,
            title="Start Investing",
            description="Begin building investment portfolio for long-term wealth",
            rationale="Investing creates wealth through compound growth; investing early maximizes returns",
            target_metric="Investment Portfolio",
            current_value="$0",
            target_value=f"${annual_investment:,.0f}/year",
            priority=RecommendationPriority.HIGH,
            estimated_impact=expected_return,
            estimated_timeframe=120,  # 10 years
            action_steps=[
                "Open brokerage account (Vanguard, Fidelity, etc)",
                "Choose low-cost index funds matching risk tolerance",
                f"Invest ${annual_investment / 12:,.0f} monthly",
            ],
        )
    
    def _recommend_increase_retirement_savings(self, profile: FinancialProfile) -> Recommendation:
        """Recommend increasing retirement savings."""
        target_retirement = profile.annual_income * 25  # 4% rule target
        gap = target_retirement - profile.retirement_savings
        monthly_needed = gap / (profile.years_to_retirement * 12)
        
        return Recommendation(
            recommendation_id=str(uuid.uuid4()),
            category=RecommendationCategory.RETIREMENT,
            title="Boost Retirement Savings",
            description="Increase contributions to reach retirement goals",
            rationale="Starting retirement savings early leverages compound growth for comfortable retirement",
            target_metric="Retirement Savings",
            current_value=f"${profile.retirement_savings:,.0f}",
            target_value=f"${target_retirement:,.0f}",
            priority=RecommendationPriority.HIGH,
            estimated_impact=monthly_needed * 0.07 * 12,  # 7% return
            estimated_timeframe=profile.years_to_retirement * 12,
            action_steps=[
                f"Increase 401(k)/IRA contributions to ${monthly_needed:,.0f}/month",
                "Maximize employer match first",
                "Use tax-advantaged accounts",
            ],
        )
    
    def _recommend_tax_optimization(self, profile: FinancialProfile) -> Recommendation:
        """Recommend tax optimization strategies."""
        potential_savings = profile.investment_portfolio_value * 0.02  # 2% tax savings
        
        return Recommendation(
            recommendation_id=str(uuid.uuid4()),
            category=RecommendationCategory.TAX_OPTIMIZATION,
            title="Implement Tax Optimization",
            description="Optimize investment strategy for tax efficiency",
            rationale="Tax-loss harvesting and strategic asset location can significantly reduce tax liability",
            target_metric="Tax Efficiency",
            current_value="Unoptimized",
            target_value="Tax-optimized",
            priority=RecommendationPriority.MEDIUM,
            estimated_impact=potential_savings,
            estimated_timeframe=12,
            action_steps=[
                "Review capital gains and losses",
                "Implement tax-loss harvesting",
                "Place tax-inefficient investments in retirement accounts",
            ],
        )
    
    def _recommend_spending_reduction(self, profile: FinancialProfile) -> Recommendation:
        """Recommend reducing spending."""
        target_spending = profile.monthly_income * 0.6
        excess = profile.monthly_expenses - target_spending
        annual_savings = excess * 12
        
        return Recommendation(
            recommendation_id=str(uuid.uuid4()),
            category=RecommendationCategory.SPENDING,
            title="Reduce Spending",
            description="Optimize budget to align with income",
            rationale="Spending exceeds healthy threshold; reducing frees up cash for savings and debt reduction",
            target_metric="Spending as % of Income",
            current_value=f"{profile.monthly_expenses / profile.monthly_income:.0%}",
            target_value="60%",
            priority=RecommendationPriority.HIGH,
            estimated_impact=annual_savings,
            estimated_timeframe=6,
            action_steps=[
                "Track and categorize all spending",
                "Identify and eliminate non-essential expenses",
                "Negotiate lower rates (insurance, subscriptions)",
            ],
        )
    
    def _recommend_umbrella_insurance(self, profile: FinancialProfile) -> Recommendation:
        """Recommend umbrella insurance."""
        annual_cost = 200  # Typical umbrella insurance cost
        coverage_protection = profile.net_worth
        
        return Recommendation(
            recommendation_id=str(uuid.uuid4()),
            category=RecommendationCategory.INSURANCE,
            title="Get Umbrella Insurance",
            description="Protect assets with umbrella liability coverage",
            rationale="High net worth requires additional protection against liability claims",
            target_metric="Liability Coverage",
            current_value="Minimal",
            target_value=f"${coverage_protection:,.0f}",
            priority=RecommendationPriority.MEDIUM,
            estimated_impact=0.0,  # Protective
            estimated_timeframe=1,
            action_steps=[
                "Review current liability coverage",
                "Get quotes for umbrella policy ($1M-$5M coverage)",
                "Compare rates from multiple insurers",
            ],
        )
    
    def _recommend_goal_setting(self, profile: FinancialProfile) -> Recommendation:
        """Recommend setting financial goals."""
        return Recommendation(
            recommendation_id=str(uuid.uuid4()),
            category=RecommendationCategory.GOAL_PLANNING,
            title="Define Financial Goals",
            description="Establish clear, measurable financial goals",
            rationale="Goals provide direction and motivation for financial planning and decision-making",
            target_metric="Financial Goals",
            current_value="None defined",
            target_value="SMART goals established",
            priority=RecommendationPriority.MEDIUM,
            estimated_impact=0.0,  # Foundational
            estimated_timeframe=1,
            action_steps=[
                "List short-term goals (1-3 years)",
                "List medium-term goals (3-10 years)",
                "List long-term goals (10+ years)",
                "Make each goal specific, measurable, actionable",
            ],
        )
