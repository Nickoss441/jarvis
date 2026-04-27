"""Financial cash flow forecasting and runway analysis.

Projects future cash flows, identifies spending patterns, calculates
financial runway, and provides cash flow forecasting insights.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from statistics import mean, median, stdev
import uuid


class CashFlowType(str, Enum):
    """Types of cash flows."""
    INCOME = "income"
    EXPENSE = "expense"
    INVESTMENT = "investment"
    SAVINGS = "savings"
    DIVIDEND = "dividend"
    BONUS = "bonus"
    TRANSFER = "transfer"
    REFUND = "refund"


class ForecastPeriod(str, Enum):
    """Forecast periods."""
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"


class CashFlowTrend(str, Enum):
    """Cash flow trends."""
    INCREASING = "increasing"
    STABLE = "stable"
    DECREASING = "decreasing"
    VOLATILE = "volatile"


@dataclass
class CashFlowEntry:
    """A cash flow transaction.
    
    Attributes:
        entry_id: Unique entry ID
        amount: Amount of cash flow (positive for inflow, negative for outflow)
        flow_type: Type of cash flow
        date: Date of cash flow
        category: Cash flow category
        description: Description
    """
    entry_id: str
    amount: float
    flow_type: CashFlowType
    date: datetime
    category: str
    description: str = ""
    
    def __post_init__(self):
        """Validate entry."""
        if not isinstance(self.date, datetime) or self.date.tzinfo is None:
            raise ValueError("date must be timezone-aware (UTC)")
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.entry_id,
            "amount": self.amount,
            "type": self.flow_type.value,
            "date": self.date.isoformat(),
            "category": self.category,
            "description": self.description,
        }


@dataclass
class MonthlyMetrics:
    """Monthly cash flow metrics.
    
    Attributes:
        year: Year
        month: Month (1-12)
        total_inflow: Total inflow for month
        total_outflow: Total outflow for month
        net_flow: Net cash flow (inflow - outflow)
        expense_count: Number of expense transactions
        income_count: Number of income transactions
    """
    year: int
    month: int
    total_inflow: float
    total_outflow: float
    net_flow: float
    expense_count: int
    income_count: int
    
    @property
    def savings_rate(self) -> float:
        """Calculate savings rate (net / inflow)."""
        if self.total_inflow <= 0:
            return 0
        return (self.net_flow / self.total_inflow) * 100
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "year": self.year,
            "month": self.month,
            "inflow": self.total_inflow,
            "outflow": self.total_outflow,
            "net": self.net_flow,
            "savings_rate": self.savings_rate,
        }


@dataclass
class CashFlowForecast:
    """Cash flow forecast for future period.
    
    Attributes:
        forecast_id: Unique forecast ID
        period_start: Start of forecast period
        period_end: End of forecast period
        forecasted_inflow: Forecasted inflow
        forecasted_outflow: Forecasted outflow
        forecasted_net: Forecasted net flow
        confidence: Confidence level (0-100)
        assumptions: List of assumptions used in forecast
    """
    forecast_id: str
    period_start: datetime
    period_end: datetime
    forecasted_inflow: float
    forecasted_outflow: float
    forecasted_net: float
    confidence: float
    assumptions: list[str] = field(default_factory=list)
    created_at: datetime = None
    
    def __post_init__(self):
        """Validate forecast."""
        if not isinstance(self.period_start, datetime) or self.period_start.tzinfo is None:
            raise ValueError("period_start must be timezone-aware (UTC)")
        if not isinstance(self.period_end, datetime) or self.period_end.tzinfo is None:
            raise ValueError("period_end must be timezone-aware (UTC)")
        if self.confidence < 0 or self.confidence > 100:
            raise ValueError("Confidence must be between 0 and 100")
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.forecast_id,
            "start": self.period_start.isoformat(),
            "end": self.period_end.isoformat(),
            "inflow": self.forecasted_inflow,
            "outflow": self.forecasted_outflow,
            "net": self.forecasted_net,
            "confidence": self.confidence,
            "assumptions": self.assumptions,
        }


@dataclass
class RunwayAnalysis:
    """Analysis of financial runway.
    
    Attributes:
        analysis_id: Unique analysis ID
        current_balance: Current cash balance
        monthly_burn_rate: Average monthly cash burn rate
        runway_months: Number of months until funds depleted
        depletion_date: Projected date when funds depleted
        status: Runway health status
        recommendations: Actionable recommendations
    """
    analysis_id: str
    current_balance: float
    monthly_burn_rate: float
    runway_months: float
    depletion_date: datetime
    status: str
    recommendations: list[str]
    generated_at: datetime = None
    
    def __post_init__(self):
        """Set defaults."""
        if self.generated_at is None:
            self.generated_at = datetime.now(timezone.utc)
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.analysis_id,
            "balance": self.current_balance,
            "burn_rate": self.monthly_burn_rate,
            "runway": self.runway_months,
            "depletion_date": self.depletion_date.isoformat() if self.depletion_date else None,
            "status": self.status,
            "recommendations": self.recommendations,
        }


class CashFlowForecaster:
    """Analyzes cash flows and forecasts future cash flow."""
    
    def __init__(self):
        """Initialize cash flow forecaster."""
        self.entries: dict[str, CashFlowEntry] = {}
        self.current_balance: float = 0.0
    
    def add_entry(
        self,
        amount: float,
        flow_type: CashFlowType,
        date: datetime,
        category: str,
        description: str = "",
    ) -> CashFlowEntry:
        """Add a cash flow entry.
        
        Args:
            amount: Cash flow amount
            flow_type: Type of cash flow
            date: Date of cash flow
            category: Category
            description: Optional description
        
        Returns:
            Created entry
        """
        entry_id = str(uuid.uuid4())
        entry = CashFlowEntry(
            entry_id=entry_id,
            amount=amount,
            flow_type=flow_type,
            date=date,
            category=category,
            description=description,
        )
        self.entries[entry_id] = entry
        return entry
    
    def set_current_balance(self, balance: float):
        """Set current cash balance.
        
        Args:
            balance: Current balance
        """
        self.current_balance = balance
    
    def get_entries_for_period(self, start_date: datetime, end_date: datetime) -> list[CashFlowEntry]:
        """Get entries for a period.
        
        Args:
            start_date: Period start
            end_date: Period end
        
        Returns:
            List of entries in period
        """
        return [
            e for e in self.entries.values()
            if start_date <= e.date <= end_date
        ]
    
    def calculate_monthly_metrics(self, year: int, month: int) -> MonthlyMetrics:
        """Calculate metrics for a month.
        
        Args:
            year: Year
            month: Month (1-12)
        
        Returns:
            Monthly metrics
        """
        # Get first and last day of month
        if month == 12:
            period_end = datetime(year + 1, 1, 1, tzinfo=timezone.utc) - timedelta(seconds=1)
        else:
            period_end = datetime(year, month + 1, 1, tzinfo=timezone.utc) - timedelta(seconds=1)
        
        period_start = datetime(year, month, 1, tzinfo=timezone.utc)
        
        entries = self.get_entries_for_period(period_start, period_end)
        
        inflow = sum(e.amount for e in entries if e.flow_type == CashFlowType.INCOME)
        outflow = abs(sum(e.amount for e in entries if e.flow_type == CashFlowType.EXPENSE))
        net = inflow - outflow
        
        expense_count = sum(1 for e in entries if e.flow_type == CashFlowType.EXPENSE)
        income_count = sum(1 for e in entries if e.flow_type == CashFlowType.INCOME)
        
        return MonthlyMetrics(
            year=year,
            month=month,
            total_inflow=inflow,
            total_outflow=outflow,
            net_flow=net,
            expense_count=expense_count,
            income_count=income_count,
        )
    
    def analyze_trends(self, num_months: int = 12) -> CashFlowTrend:
        """Analyze cash flow trends over recent months.
        
        Args:
            num_months: Number of months to analyze
        
        Returns:
            Trend classification
        """
        now = datetime.now(timezone.utc)
        monthly_nets = []
        
        for i in range(num_months):
            # Calculate month to analyze
            analysis_month = now - timedelta(days=30 * i)
            metrics = self.calculate_monthly_metrics(analysis_month.year, analysis_month.month)
            monthly_nets.append(metrics.net_flow)
        
        if not monthly_nets or len(monthly_nets) < 2:
            return CashFlowTrend.STABLE
        
        # Check trend
        recent = monthly_nets[:3]
        older = monthly_nets[-3:]
        
        recent_avg = mean(recent) if recent else 0
        older_avg = mean(older) if older else 0
        
        if recent_avg > older_avg * 1.1:
            return CashFlowTrend.INCREASING
        elif recent_avg < older_avg * 0.9:
            return CashFlowTrend.DECREASING
        else:
            # Check volatility
            if len(monthly_nets) >= 3:
                try:
                    std = stdev(monthly_nets)
                    avg = mean(monthly_nets)
                    if avg != 0 and (std / abs(avg)) > 0.3:
                        return CashFlowTrend.VOLATILE
                except ValueError:
                    pass
            return CashFlowTrend.STABLE
    
    def forecast_cash_flow(self, periods_ahead: int = 3, period_type: ForecastPeriod = ForecastPeriod.MONTHLY) -> CashFlowForecast:
        """Forecast future cash flow.
        
        Args:
            periods_ahead: Number of periods to forecast
            period_type: Type of period
        
        Returns:
            Cash flow forecast
        """
        now = datetime.now(timezone.utc)
        
        # Calculate average monthly inflow/outflow from last 6 months
        inflows = []
        outflows = []
        
        for i in range(6):
            analysis_month = now - timedelta(days=30 * i)
            try:
                metrics = self.calculate_monthly_metrics(analysis_month.year, analysis_month.month)
                inflows.append(metrics.total_inflow)
                outflows.append(metrics.total_outflow)
            except (ValueError, IndexError):
                pass
        
        avg_inflow = mean(inflows) if inflows else 0
        avg_outflow = mean(outflows) if outflows else 0
        
        # Project forward
        if period_type == ForecastPeriod.MONTHLY:
            forecast_inflow = avg_inflow * periods_ahead
            forecast_outflow = avg_outflow * periods_ahead
            days_ahead = 30 * periods_ahead
        elif period_type == ForecastPeriod.QUARTERLY:
            forecast_inflow = avg_inflow * 3 * periods_ahead
            forecast_outflow = avg_outflow * 3 * periods_ahead
            days_ahead = 90 * periods_ahead
        else:  # ANNUAL
            forecast_inflow = avg_inflow * 12 * periods_ahead
            forecast_outflow = avg_outflow * 12 * periods_ahead
            days_ahead = 365 * periods_ahead
        
        period_start = now
        period_end = now + timedelta(days=days_ahead)
        
        # Calculate confidence based on data consistency
        confidence = 50
        if len(inflows) == 6:
            try:
                if stdev(inflows) < mean(inflows) * 0.2:
                    confidence = 75
            except ValueError:
                pass
        
        return CashFlowForecast(
            forecast_id=str(uuid.uuid4()),
            period_start=period_start,
            period_end=period_end,
            forecasted_inflow=forecast_inflow,
            forecasted_outflow=forecast_outflow,
            forecasted_net=forecast_inflow - forecast_outflow,
            confidence=confidence,
            assumptions=[
                f"Based on average of last 6 months",
                f"Assumes {period_type.value} growth pattern continues",
                f"No major life changes or economic shocks",
            ],
        )
    
    def analyze_runway(self, monthly_burn_rate: float = None) -> RunwayAnalysis:
        """Analyze financial runway.
        
        Args:
            monthly_burn_rate: Optional explicit burn rate (defaults to average)
        
        Returns:
            Runway analysis
        """
        if monthly_burn_rate is None:
            # Calculate from last 3 months
            now = datetime.now(timezone.utc)
            net_flows = []
            for i in range(3):
                analysis_month = now - timedelta(days=30 * i)
                try:
                    metrics = self.calculate_monthly_metrics(analysis_month.year, analysis_month.month)
                    net_flows.append(metrics.net_flow)
                except (ValueError, IndexError):
                    pass
            
            monthly_burn_rate = -min(net_flows) if net_flows and min(net_flows) < 0 else 0
        
        # Calculate runway
        if monthly_burn_rate > 0:
            runway_months = self.current_balance / monthly_burn_rate
        else:
            runway_months = float('inf')
        
        # Calculate depletion date
        now = datetime.now(timezone.utc)
        if runway_months != float('inf'):
            depletion_date = now + timedelta(days=runway_months * 30)
        else:
            depletion_date = now + timedelta(days=365 * 10)  # 10 years out
        
        # Status
        if runway_months > 12:
            status = "healthy"
        elif runway_months > 6:
            status = "caution"
        elif runway_months > 3:
            status = "warning"
        else:
            status = "critical"
        
        # Recommendations
        recommendations = []
        if monthly_burn_rate > 0:
            recommendations.append(f"Average monthly burn rate: ${monthly_burn_rate:.2f}")
        
        if status == "critical":
            recommendations.append("⚠️ Critical: Increase income or reduce expenses immediately")
        elif status == "warning":
            recommendations.append("⚠️ Warning: Develop plan to reduce burn rate within 3 months")
        elif status == "caution":
            recommendations.append("Monitor: Plan cost reductions for sustainability beyond 1 year")
        
        return RunwayAnalysis(
            analysis_id=str(uuid.uuid4()),
            current_balance=self.current_balance,
            monthly_burn_rate=monthly_burn_rate,
            runway_months=runway_months if runway_months != float('inf') else 999,
            depletion_date=depletion_date,
            status=status,
            recommendations=recommendations,
        )
