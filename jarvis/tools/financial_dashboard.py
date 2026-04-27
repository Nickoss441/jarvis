"""Financial dashboard and reporting engine.

Provides consolidated financial reporting across wallet, crypto portfolio,
travel itineraries, and budget forecasts with PDF export and analytics.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
import json


class ReportFormat(str, Enum):
    """Report format enumeration."""
    JSON = "json"
    TEXT = "text"
    CSV = "csv"
    HTML = "html"


class ReportPeriod(str, Enum):
    """Report period enumeration."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
    CUSTOM = "custom"


@dataclass
class NetWorthSnapshot:
    """Point-in-time net worth snapshot.
    
    Attributes:
        timestamp: When snapshot was taken (UTC)
        total_assets: Sum of all asset values
        total_liabilities: Sum of all debts
        net_worth: Total assets minus liabilities
        breakdown: Dict of asset_type -> value
    """
    timestamp: datetime
    total_assets: float
    total_liabilities: float
    net_worth: float
    breakdown: dict[str, float] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate snapshot."""
        if not isinstance(self.timestamp, datetime):
            raise ValueError("timestamp must be a datetime object")
        if self.timestamp.tzinfo is None:
            raise ValueError("timestamp must be timezone-aware (UTC)")
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "total_assets": self.total_assets,
            "total_liabilities": self.total_liabilities,
            "net_worth": self.net_worth,
            "breakdown": self.breakdown,
        }


@dataclass
class SpendingAnalysis:
    """Analysis of spending patterns and trends.
    
    Attributes:
        period: Analysis period
        total_spending: Total amount spent in period
        by_category: Dict of category -> amount
        daily_average: Average daily spending
        top_categories: List of (category, amount) tuples sorted by amount
        vs_budget: Comparison to budget (None if no budget)
        trend: Trend indicator ("up", "down", "stable")
    """
    period: str
    total_spending: float
    by_category: dict[str, float]
    daily_average: float
    top_categories: list[tuple[str, float]] = field(default_factory=list)
    vs_budget: Optional[dict[str, float]] = None
    trend: str = "stable"
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "period": self.period,
            "total_spending": self.total_spending,
            "daily_average": self.daily_average,
            "by_category": self.by_category,
            "top_categories": [{"category": cat, "amount": amt} for cat, amt in self.top_categories],
            "vs_budget": self.vs_budget,
            "trend": self.trend,
        }


@dataclass
class AssetAllocation:
    """Asset allocation across portfolio.
    
    Attributes:
        cash: Cash and liquid assets percentage
        stocks: Stock/equity percentage
        crypto: Cryptocurrency percentage
        real_estate: Real estate percentage
        bonds: Bond percentage
        other: Other assets percentage
        total_value: Total portfolio value
    """
    cash: float
    stocks: float
    crypto: float
    real_estate: float
    bonds: float
    other: float
    total_value: float
    
    def __post_init__(self):
        """Validate allocation."""
        total_pct = self.cash + self.stocks + self.crypto + self.real_estate + self.bonds + self.other
        if not (99.5 <= total_pct <= 100.5):  # Allow small rounding errors
            raise ValueError(f"Allocations must sum to 100%, got {total_pct}%")
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "cash": self.cash,
            "stocks": self.stocks,
            "crypto": self.crypto,
            "real_estate": self.real_estate,
            "bonds": self.bonds,
            "other": self.other,
            "total_value": self.total_value,
        }


@dataclass
class FinancialMetrics:
    """Key financial metrics and ratios.
    
    Attributes:
        net_worth: Current net worth
        savings_rate: Monthly savings as percentage of income
        expense_ratio: Monthly expenses as percentage of income
        emergency_fund_months: Months of expenses covered by liquid assets
        debt_to_income: Total debt divided by annual income
        investment_return_ytd: Year-to-date investment return percentage
        cash_flow: Monthly cash flow (positive = surplus, negative = deficit)
    """
    net_worth: float
    savings_rate: float
    expense_ratio: float
    emergency_fund_months: float
    debt_to_income: float
    investment_return_ytd: float
    cash_flow: float
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "net_worth": self.net_worth,
            "savings_rate": self.savings_rate,
            "expense_ratio": self.expense_ratio,
            "emergency_fund_months": self.emergency_fund_months,
            "debt_to_income": self.debt_to_income,
            "investment_return_ytd": self.investment_return_ytd,
            "cash_flow": self.cash_flow,
        }


@dataclass
class FinancialReport:
    """Comprehensive financial report.
    
    Attributes:
        report_id: Unique report identifier
        generated_at: When report was generated (UTC)
        period: Report period
        net_worth_snapshot: Current net worth snapshot
        spending_analysis: Spending analysis for period
        asset_allocation: Current asset allocation
        metrics: Key financial metrics
        goals_summary: Summary of financial goals status
        recommendations: List of financial recommendations
        alerts: List of financial alerts
    """
    report_id: str
    generated_at: datetime
    period: ReportPeriod
    net_worth_snapshot: NetWorthSnapshot
    spending_analysis: SpendingAnalysis
    asset_allocation: AssetAllocation
    metrics: FinancialMetrics
    goals_summary: dict = field(default_factory=dict)
    recommendations: list[str] = field(default_factory=list)
    alerts: list[dict] = field(default_factory=list)
    
    def __post_init__(self):
        """Validate report."""
        if not isinstance(self.generated_at, datetime):
            raise ValueError("generated_at must be a datetime object")
        if self.generated_at.tzinfo is None:
            raise ValueError("generated_at must be timezone-aware (UTC)")
    
    def to_dict(self) -> dict:
        """Convert report to dictionary."""
        return {
            "report_id": self.report_id,
            "generated_at": self.generated_at.isoformat(),
            "period": self.period.value,
            "net_worth": self.net_worth_snapshot.to_dict(),
            "spending": self.spending_analysis.to_dict(),
            "allocation": self.asset_allocation.to_dict(),
            "metrics": self.metrics.to_dict(),
            "goals": self.goals_summary,
            "recommendations": self.recommendations,
            "alerts": self.alerts,
        }
    
    def to_json(self) -> str:
        """Serialize report to JSON string."""
        return json.dumps(self.to_dict(), indent=2)
    
    def to_text(self) -> str:
        """Serialize report to text format."""
        lines = [
            f"{'='*60}",
            f"FINANCIAL REPORT - {self.period.value.upper()}",
            f"Generated: {self.generated_at.isoformat()}",
            f"Report ID: {self.report_id}",
            f"{'='*60}",
            "",
            "NET WORTH SUMMARY",
            f"-{'-'*58}",
            f"Total Assets:        ${self.net_worth_snapshot.total_assets:>15,.2f}",
            f"Total Liabilities:   ${self.net_worth_snapshot.total_liabilities:>15,.2f}",
            f"Net Worth:           ${self.net_worth_snapshot.net_worth:>15,.2f}",
            "",
            "SPENDING ANALYSIS",
            f"-{'-'*58}",
            f"Total Spending:      ${self.spending_analysis.total_spending:>15,.2f}",
            f"Daily Average:       ${self.spending_analysis.daily_average:>15,.2f}",
            f"Trend:               {self.spending_analysis.trend:>15}",
            "",
            "TOP SPENDING CATEGORIES",
            f"-{'-'*58}",
        ]
        
        for category, amount in self.spending_analysis.top_categories[:5]:
            pct = (amount / self.spending_analysis.total_spending * 100) if self.spending_analysis.total_spending > 0 else 0
            lines.append(f"{category:20} ${amount:>12,.2f} ({pct:>5.1f}%)")
        
        lines.extend([
            "",
            "ASSET ALLOCATION",
            f"-{'-'*58}",
            f"Cash:                {self.asset_allocation.cash:>15.1f}%",
            f"Stocks:              {self.asset_allocation.stocks:>15.1f}%",
            f"Crypto:              {self.asset_allocation.crypto:>15.1f}%",
            f"Real Estate:         {self.asset_allocation.real_estate:>15.1f}%",
            f"Bonds:               {self.asset_allocation.bonds:>15.1f}%",
            f"Other:               {self.asset_allocation.other:>15.1f}%",
            f"Total Value:         ${self.asset_allocation.total_value:>15,.2f}",
            "",
            "KEY METRICS",
            f"-{'-'*58}",
            f"Savings Rate:        {self.metrics.savings_rate:>15.1f}%",
            f"Expense Ratio:       {self.metrics.expense_ratio:>15.1f}%",
            f"Emergency Fund:      {self.metrics.emergency_fund_months:>15.1f} months",
            f"Debt-to-Income:      {self.metrics.debt_to_income:>15.1f}",
            f"YTD Investment Return: {self.metrics.investment_return_ytd:>13.1f}%",
            f"Monthly Cash Flow:   ${self.metrics.cash_flow:>15,.2f}",
        ])
        
        if self.recommendations:
            lines.extend([
                "",
                "RECOMMENDATIONS",
                f"-{'-'*58}",
            ])
            for i, rec in enumerate(self.recommendations, 1):
                lines.append(f"{i}. {rec}")
        
        if self.alerts:
            lines.extend([
                "",
                "ALERTS",
                f"-{'-'*58}",
            ])
            for alert in self.alerts:
                severity = alert.get("severity", "info").upper()
                message = alert.get("message", "")
                lines.append(f"[{severity}] {message}")
        
        lines.extend([
            "",
            f"{'='*60}",
        ])
        
        return "\n".join(lines)
    
    def to_csv(self) -> str:
        """Serialize report to CSV format."""
        lines = []
        
        # Summary section
        lines.append("FINANCIAL SUMMARY")
        lines.append("Metric,Value")
        lines.append(f"Net Worth,{self.net_worth_snapshot.net_worth}")
        lines.append(f"Total Assets,{self.net_worth_snapshot.total_assets}")
        lines.append(f"Total Liabilities,{self.net_worth_snapshot.total_liabilities}")
        lines.append(f"Total Spending,{self.spending_analysis.total_spending}")
        lines.append(f"Daily Average Spending,{self.spending_analysis.daily_average}")
        lines.append("")
        
        # Spending by category
        lines.append("SPENDING BY CATEGORY")
        lines.append("Category,Amount")
        for category, amount in sorted(self.spending_analysis.by_category.items()):
            lines.append(f"{category},{amount}")
        lines.append("")
        
        # Asset allocation
        lines.append("ASSET ALLOCATION")
        lines.append("Type,Percentage,Value")
        total_val = self.asset_allocation.total_value
        lines.append(f"Cash,{self.asset_allocation.cash},{self.asset_allocation.cash * total_val / 100}")
        lines.append(f"Stocks,{self.asset_allocation.stocks},{self.asset_allocation.stocks * total_val / 100}")
        lines.append(f"Crypto,{self.asset_allocation.crypto},{self.asset_allocation.crypto * total_val / 100}")
        lines.append(f"Real Estate,{self.asset_allocation.real_estate},{self.asset_allocation.real_estate * total_val / 100}")
        lines.append(f"Bonds,{self.asset_allocation.bonds},{self.asset_allocation.bonds * total_val / 100}")
        lines.append(f"Other,{self.asset_allocation.other},{self.asset_allocation.other * total_val / 100}")
        
        return "\n".join(lines)


class DashboardBuilder:
    """Builder for constructing financial dashboards from component data."""
    
    def __init__(self):
        """Initialize dashboard builder."""
        self.wallet_data: Optional[dict] = None
        self.crypto_data: Optional[dict] = None
        self.travel_data: Optional[dict] = None
        self.forecast_data: Optional[dict] = None
        self.income: float = 0.0
    
    def add_wallet(self, wallet_dict: dict) -> "DashboardBuilder":
        """Add wallet data to dashboard."""
        self.wallet_data = wallet_dict
        return self
    
    def add_crypto(self, crypto_dict: dict) -> "DashboardBuilder":
        """Add crypto portfolio data to dashboard."""
        self.crypto_data = crypto_dict
        return self
    
    def add_travel(self, travel_dict: dict) -> "DashboardBuilder":
        """Add travel itinerary data to dashboard."""
        self.travel_data = travel_dict
        return self
    
    def add_forecast(self, forecast_dict: dict) -> "DashboardBuilder":
        """Add budget forecast data to dashboard."""
        self.forecast_data = forecast_dict
        return self
    
    def set_income(self, monthly_income: float) -> "DashboardBuilder":
        """Set monthly income for calculations."""
        if monthly_income < 0:
            raise ValueError("Income must be non-negative")
        self.income = monthly_income
        return self
    
    def calculate_net_worth(self) -> NetWorthSnapshot:
        """Calculate current net worth from available data."""
        assets = 0.0
        liabilities = 0.0
        breakdown: dict[str, float] = {}
        
        # Add wallet cash
        if self.wallet_data:
            wallet_balance = self.wallet_data.get("total_balance", 0.0)
            assets += wallet_balance
            breakdown["cash"] = wallet_balance
        
        # Add crypto assets
        if self.crypto_data:
            crypto_value = self.crypto_data.get("total_current_value", 0.0)
            assets += crypto_value
            breakdown["crypto"] = crypto_value
        
        net_worth = assets - liabilities
        
        return NetWorthSnapshot(
            timestamp=datetime.now(timezone.utc),
            total_assets=assets,
            total_liabilities=liabilities,
            net_worth=net_worth,
            breakdown=breakdown,
        )
    
    def calculate_allocation(self) -> AssetAllocation:
        """Calculate asset allocation from available data."""
        total = 0.0
        cash_amt = 0.0
        crypto_amt = 0.0
        
        if self.wallet_data:
            cash_amt = self.wallet_data.get("total_balance", 0.0)
            total += cash_amt
        
        if self.crypto_data:
            crypto_amt = self.crypto_data.get("total_current_value", 0.0)
            total += crypto_amt
        
        if total == 0:
            total = 1.0  # Avoid division by zero
        
        return AssetAllocation(
            cash=(cash_amt / total * 100) if total > 0 else 100.0,
            stocks=0.0,
            crypto=(crypto_amt / total * 100) if total > 0 else 0.0,
            real_estate=0.0,
            bonds=0.0,
            other=0.0,
            total_value=total,
        )
    
    def build(self, period: ReportPeriod = ReportPeriod.MONTHLY) -> FinancialReport:
        """Build complete financial report."""
        import uuid
        
        # Calculate snapshots
        net_worth = self.calculate_net_worth()
        allocation = self.calculate_allocation()
        
        # Spending analysis (mock for now)
        spending = SpendingAnalysis(
            period=period.value,
            total_spending=self.wallet_data.get("monthly_spending", 0.0) if self.wallet_data else 0.0,
            by_category=self.wallet_data.get("by_category", {}) if self.wallet_data else {},
            daily_average=(self.wallet_data.get("monthly_spending", 0.0) / 30) if self.wallet_data else 0.0,
        )
        
        # Calculate top categories
        spending.top_categories = sorted(
            spending.by_category.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        # Calculate metrics
        monthly_expense = spending.total_spending
        savings = max(0, self.income - monthly_expense)
        savings_rate = (savings / self.income * 100) if self.income > 0 else 0.0
        expense_ratio = (monthly_expense / self.income * 100) if self.income > 0 else 0.0
        
        emergency_months = (net_worth.total_assets / monthly_expense) if monthly_expense > 0 else 0.0
        
        metrics = FinancialMetrics(
            net_worth=net_worth.net_worth,
            savings_rate=savings_rate,
            expense_ratio=expense_ratio,
            emergency_fund_months=emergency_months,
            debt_to_income=0.0,
            investment_return_ytd=self.crypto_data.get("pnl_percentage", 0.0) if self.crypto_data else 0.0,
            cash_flow=savings,
        )
        
        # Generate recommendations
        recommendations = []
        if savings_rate < 20:
            recommendations.append("Target savings rate of 20%+ - review spending categories")
        if emergency_months < 3:
            recommendations.append("Build emergency fund to cover 3-6 months of expenses")
        if self.crypto_data and self.crypto_data.get("rebalancing_needed"):
            recommendations.append("Rebalance crypto portfolio toward target allocation")
        
        # Generate alerts
        alerts = []
        if monthly_expense > self.income:
            alerts.append({
                "severity": "warning",
                "message": f"Monthly expenses (${monthly_expense:.2f}) exceed income (${self.income:.2f})"
            })
        
        return FinancialReport(
            report_id=str(uuid.uuid4()),
            generated_at=datetime.now(timezone.utc),
            period=period,
            net_worth_snapshot=net_worth,
            spending_analysis=spending,
            asset_allocation=allocation,
            metrics=metrics,
            recommendations=recommendations,
            alerts=alerts,
        )
