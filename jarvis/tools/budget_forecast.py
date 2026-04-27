"""Budget forecasting and projections engine.

Provides predictive spending analysis, budget forecasting, goal tracking,
and financial planning with integration to wallet data.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Optional
import statistics


class ForecastMethod(str, Enum):
    """Forecasting method enumeration."""
    SIMPLE_AVERAGE = "simple_average"
    WEIGHTED_AVERAGE = "weighted_average"
    TREND = "trend"
    SEASONAL = "seasonal"


class GoalType(str, Enum):
    """Financial goal type enumeration."""
    SAVINGS = "savings"
    DEBT_PAYOFF = "debt_payoff"
    INVESTMENT = "investment"
    EMERGENCY_FUND = "emergency_fund"
    VACATION = "vacation"
    EDUCATION = "education"
    HOME = "home"
    RETIREMENT = "retirement"


@dataclass
class MonthlySpendingData:
    """Historical monthly spending data for analysis.
    
    Attributes:
        year: Year of the data
        month: Month of the data (1-12)
        total_spending: Total spending for the month
        by_category: Dict of category -> amount
        account_id: Associated account (optional)
    """
    year: int
    month: int
    total_spending: float
    by_category: dict[str, float]
    account_id: Optional[str] = None
    
    def __post_init__(self):
        """Validate spending data."""
        if not 1 <= self.month <= 12:
            raise ValueError(f"Month must be 1-12, got {self.month}")
        if self.total_spending < 0:
            raise ValueError(f"Total spending must be non-negative, got {self.total_spending}")
        if sum(self.by_category.values()) < 0:
            raise ValueError("Category amounts must be non-negative")


@dataclass
class SpendingForecast:
    """Spending forecast for a time period.
    
    Attributes:
        year: Forecast year
        month: Forecast month (1-12)
        forecast_amount: Predicted spending amount
        confidence: Confidence level (0.0-1.0)
        method: Forecasting method used
        by_category: Dict of category -> forecasted amount
    """
    year: int
    month: int
    forecast_amount: float
    confidence: float
    method: ForecastMethod
    by_category: dict[str, float] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate forecast."""
        if not 1 <= self.month <= 12:
            raise ValueError(f"Month must be 1-12, got {self.month}")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be 0.0-1.0, got {self.confidence}")
        if self.forecast_amount < 0:
            raise ValueError(f"Forecast amount must be non-negative")


@dataclass
class FinancialGoal:
    """A financial goal with target and timeline.
    
    Attributes:
        goal_id: Unique goal identifier
        name: Goal name
        goal_type: Type of goal
        target_amount: Target amount in USD
        current_amount: Current progress toward goal
        deadline: Target date for goal completion
        created_at: When goal was created (UTC)
        category: Category this spending goes to (optional)
    """
    goal_id: str
    name: str
    goal_type: GoalType
    target_amount: float
    current_amount: float
    deadline: datetime
    created_at: datetime
    category: Optional[str] = None
    
    def __post_init__(self):
        """Validate goal."""
        if self.target_amount <= 0:
            raise ValueError(f"Target amount must be positive, got {self.target_amount}")
        if self.current_amount < 0:
            raise ValueError(f"Current amount must be non-negative, got {self.current_amount}")
        if self.current_amount > self.target_amount:
            raise ValueError(f"Current amount ({self.current_amount}) exceeds target ({self.target_amount})")
        if not isinstance(self.deadline, datetime):
            raise ValueError("deadline must be a datetime object")
        if self.deadline.tzinfo is None:
            raise ValueError("deadline must be timezone-aware (UTC)")
        if not isinstance(self.created_at, datetime):
            raise ValueError("created_at must be a datetime object")
        if self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware (UTC)")
    
    def progress_percent(self) -> float:
        """Calculate progress percentage."""
        if self.target_amount == 0:
            return 0.0
        return (self.current_amount / self.target_amount) * 100
    
    def remaining_amount(self) -> float:
        """Calculate remaining amount needed."""
        return max(0, self.target_amount - self.current_amount)
    
    def days_remaining(self, as_of: datetime = None) -> int:
        """Calculate days until deadline."""
        if as_of is None:
            as_of = datetime.now(timezone.utc)
        
        delta = self.deadline - as_of
        return max(0, delta.days)
    
    def is_on_track(self, monthly_contribution: float) -> bool:
        """Check if goal is on track for completion."""
        remaining = self.remaining_amount()
        if remaining <= 0:
            return True
        
        months_remaining = self.days_remaining() / 30.0
        if months_remaining <= 0:
            return False
        
        required_monthly = remaining / months_remaining
        return monthly_contribution >= required_monthly
    
    def to_dict(self) -> dict:
        """Convert goal to dictionary."""
        return {
            "goal_id": self.goal_id,
            "name": self.name,
            "goal_type": self.goal_type.value,
            "target_amount": self.target_amount,
            "current_amount": self.current_amount,
            "progress_percent": self.progress_percent(),
            "remaining_amount": self.remaining_amount(),
            "deadline": self.deadline.isoformat(),
            "days_remaining": self.days_remaining(),
            "created_at": self.created_at.isoformat(),
        }


class BudgetForecaster:
    """Forecasting engine for budget prediction and analysis."""
    
    def __init__(self, min_data_points: int = 3):
        """Initialize forecaster.
        
        Args:
            min_data_points: Minimum historical data points required for forecasting
        """
        self.min_data_points = min_data_points
        self.spending_history: list[MonthlySpendingData] = []
    
    def add_historical_data(self, data: MonthlySpendingData) -> None:
        """Add historical spending data."""
        # Check for duplicates
        for existing in self.spending_history:
            if existing.year == data.year and existing.month == data.month and existing.account_id == data.account_id:
                raise ValueError(f"Data already exists for {data.year}-{data.month:02d}")
        
        self.spending_history.append(data)
        # Sort by date
        self.spending_history.sort(key=lambda x: (x.year, x.month))
    
    def forecast_simple_average(self, months_ahead: int = 1) -> list[SpendingForecast]:
        """Forecast using simple average of historical data."""
        if len(self.spending_history) < self.min_data_points:
            raise ValueError(f"Need at least {self.min_data_points} data points, have {len(self.spending_history)}")
        
        total_spending = sum(data.total_spending for data in self.spending_history)
        avg_spending = total_spending / len(self.spending_history)
        
        # Calculate category averages
        categories: dict[str, list[float]] = {}
        for data in self.spending_history:
            for category, amount in data.by_category.items():
                if category not in categories:
                    categories[category] = []
                categories[category].append(amount)
        
        category_averages = {cat: sum(amounts) / len(amounts) for cat, amounts in categories.items()}
        
        # Generate forecasts
        last_date = self.spending_history[-1]
        forecasts = []
        
        for i in range(1, months_ahead + 1):
            year = last_date.year
            month = last_date.month + i
            
            # Handle year rollover
            while month > 12:
                month -= 12
                year += 1
            
            confidence = min(0.95, 0.5 + (len(self.spending_history) * 0.05))
            
            forecast = SpendingForecast(
                year=year,
                month=month,
                forecast_amount=avg_spending,
                confidence=confidence,
                method=ForecastMethod.SIMPLE_AVERAGE,
                by_category=category_averages.copy(),
            )
            forecasts.append(forecast)
        
        return forecasts
    
    def forecast_trend(self, months_ahead: int = 1) -> list[SpendingForecast]:
        """Forecast using trend analysis (linear regression approximation)."""
        if len(self.spending_history) < self.min_data_points:
            raise ValueError(f"Need at least {self.min_data_points} data points, have {len(self.spending_history)}")
        
        # Simple linear regression
        n = len(self.spending_history)
        x_values = list(range(n))
        y_values = [data.total_spending for data in self.spending_history]
        
        x_mean = statistics.mean(x_values)
        y_mean = statistics.mean(y_values)
        
        # Calculate slope
        numerator = sum((x_values[i] - x_mean) * (y_values[i] - y_mean) for i in range(n))
        denominator = sum((x_values[i] - x_mean) ** 2 for i in range(n))
        
        if denominator == 0:
            # Flat trend - fall back to average
            return self.forecast_simple_average(months_ahead)
        
        slope = numerator / denominator
        intercept = y_mean - slope * x_mean
        
        # Generate forecasts
        last_date = self.spending_history[-1]
        forecasts = []
        
        for i in range(1, months_ahead + 1):
            year = last_date.year
            month = last_date.month + i
            
            while month > 12:
                month -= 12
                year += 1
            
            # Predict based on trend
            x_pred = n + i - 1
            forecast_amount = max(0, intercept + slope * x_pred)
            
            confidence = min(0.85, 0.4 + (len(self.spending_history) * 0.05))
            
            forecast = SpendingForecast(
                year=year,
                month=month,
                forecast_amount=forecast_amount,
                confidence=confidence,
                method=ForecastMethod.TREND,
            )
            forecasts.append(forecast)
        
        return forecasts
    
    def forecast_seasonal(self, months_ahead: int = 1) -> list[SpendingForecast]:
        """Forecast using seasonal patterns."""
        if len(self.spending_history) < 12:
            # Not enough data for seasonal analysis
            return self.forecast_simple_average(months_ahead)
        
        # Calculate seasonal factors by month
        by_month: dict[int, list[float]] = {}
        for data in self.spending_history:
            if data.month not in by_month:
                by_month[data.month] = []
            by_month[data.month].append(data.total_spending)
        
        seasonal_factors = {month: statistics.mean(amounts) for month, amounts in by_month.items()}
        
        # Overall average - extract just the spending amounts
        recent_spending = [d.total_spending for d in self.spending_history[-12:]] if len(self.spending_history) >= 12 else [d.total_spending for d in self.spending_history]
        overall_avg = statistics.mean(recent_spending)
        
        # Generate forecasts
        last_date = self.spending_history[-1]
        forecasts = []
        
        for i in range(1, months_ahead + 1):
            year = last_date.year
            month = last_date.month + i
            
            while month > 12:
                month -= 12
                year += 1
            
            # Get seasonal factor for this month
            seasonal_factor = seasonal_factors.get(month, overall_avg)
            forecast_amount = seasonal_factor
            
            confidence = min(0.90, 0.6 + (len(self.spending_history) * 0.02))
            
            forecast = SpendingForecast(
                year=year,
                month=month,
                forecast_amount=forecast_amount,
                confidence=confidence,
                method=ForecastMethod.SEASONAL,
            )
            forecasts.append(forecast)
        
        return forecasts
    
    def get_best_forecast(self, months_ahead: int = 1) -> SpendingForecast:
        """Get best forecast using all methods and selecting highest confidence."""
        if len(self.spending_history) < self.min_data_points:
            raise ValueError(f"Need at least {self.min_data_points} data points")
        
        try:
            simple = self.forecast_simple_average(months_ahead)[0]
        except:
            simple = None
        
        try:
            trend = self.forecast_trend(months_ahead)[0]
        except:
            trend = None
        
        try:
            seasonal = self.forecast_seasonal(months_ahead)[0]
        except:
            seasonal = None
        
        forecasts = [f for f in [simple, trend, seasonal] if f is not None]
        if not forecasts:
            raise ValueError("Unable to generate any forecasts")
        
        # Return forecast with highest confidence
        return max(forecasts, key=lambda f: f.confidence)


@dataclass
class FinancialForecast:
    """Complete financial forecast for a time period.
    
    Attributes:
        forecast_date: Date this forecast was generated
        spending_forecast: Predicted spending
        savings_forecast: Predicted savings
        goals_progress: Dict of goal_id -> progress prediction
        recommendations: List of financial recommendations
    """
    forecast_date: datetime
    spending_forecast: SpendingForecast
    savings_forecast: Optional[float] = None
    goals_progress: dict[str, dict] = field(default_factory=dict)
    recommendations: list[str] = field(default_factory=list)


def generate_financial_forecast(
    spending_history: list[MonthlySpendingData],
    income: float,
    goals: list[FinancialGoal],
    months_ahead: int = 3
) -> FinancialForecast:
    """Generate comprehensive financial forecast."""
    forecaster = BudgetForecaster()
    
    for data in spending_history:
        forecaster.add_historical_data(data)
    
    # Get spending forecast
    spending_forecast = forecaster.get_best_forecast(months_ahead)
    
    # Calculate savings forecast
    savings_forecast = income - spending_forecast.forecast_amount
    
    # Analyze goal progress
    goals_progress: dict[str, dict] = {}
    recommendations: list[str] = []
    
    for goal in goals:
        monthly_needed = goal.remaining_amount() / max(1, goal.days_remaining() / 30.0)
        is_on_track = goal.is_on_track(savings_forecast) if savings_forecast > 0 else False
        
        goals_progress[goal.goal_id] = {
            "name": goal.name,
            "progress_percent": goal.progress_percent(),
            "remaining_amount": goal.remaining_amount(),
            "monthly_needed": monthly_needed,
            "on_track": is_on_track,
        }
        
        if not is_on_track and goal.days_remaining() > 0:
            recommendations.append(f"Increase contributions to '{goal.name}' by ${monthly_needed - savings_forecast:.2f}/month")
    
    if savings_forecast < 0:
        recommendations.append("Spending forecast exceeds projected income - review budget categories")
    
    if spending_forecast.confidence < 0.65:
        recommendations.append("Limited historical data - forecast confidence is low, collect more spending data")
    
    return FinancialForecast(
        forecast_date=datetime.now(timezone.utc),
        spending_forecast=spending_forecast,
        savings_forecast=savings_forecast,
        goals_progress=goals_progress,
        recommendations=recommendations,
    )
