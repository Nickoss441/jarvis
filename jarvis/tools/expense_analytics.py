"""Expense analytics and insights engine.

Provides advanced analysis of spending patterns, anomaly detection,
and actionable insights for expense optimization.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
import statistics
import uuid


class AnomalyType(str, Enum):
    """Types of spending anomalies."""
    UNUSUALLY_HIGH = "unusually_high"
    UNUSUALLY_LOW = "unusually_low"
    TREND_BREAK = "trend_break"
    CATEGORY_SPIKE = "category_spike"


class InsightSeverity(str, Enum):
    """Severity levels for insights."""
    INFO = "info"
    NOTICE = "notice"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class SpendingPattern:
    """Historical spending pattern for a category.
    
    Attributes:
        category: Expense category name
        monthly_amounts: List of monthly spending amounts
        average: Average monthly spending
        median: Median monthly spending
        std_dev: Standard deviation of spending
        trend: Trend indicator ("increasing", "decreasing", "stable")
        trend_slope: Monthly change rate (positive = increasing)
    """
    category: str
    monthly_amounts: list[float]
    average: float
    median: float
    std_dev: float
    trend: str
    trend_slope: float
    
    def __post_init__(self):
        """Validate pattern."""
        if not self.monthly_amounts:
            raise ValueError("monthly_amounts cannot be empty")
        if self.average < 0 or self.median < 0:
            raise ValueError("Amounts must be non-negative")


@dataclass
class SpendingAnomaly:
    """Detected spending anomaly.
    
    Attributes:
        anomaly_type: Type of anomaly detected
        category: Category with anomaly
        amount: Anomalous amount
        expected_range: (min, max) expected range
        severity: Severity level
        message: Description of anomaly
        timestamp: When detected (UTC)
    """
    anomaly_type: AnomalyType
    category: str
    amount: float
    expected_range: tuple[float, float]
    severity: InsightSeverity
    message: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def __post_init__(self):
        """Validate anomaly."""
        if self.amount < 0:
            raise ValueError("Amount must be non-negative")
        if self.expected_range[0] < 0 or self.expected_range[1] < 0:
            raise ValueError("Range values must be non-negative")


@dataclass
class CategoryInsight:
    """Insights for a spending category.
    
    Attributes:
        category: Category name
        current_amount: Current month spending
        average_amount: Historical average
        vs_average: Percentage difference from average
        trend: Category trend (increasing/decreasing/stable)
        rank: Rank among all categories (1 = highest)
        recommendations: List of recommendations for this category
    """
    category: str
    current_amount: float
    average_amount: float
    vs_average: float
    trend: str
    rank: int
    recommendations: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "category": self.category,
            "current": self.current_amount,
            "average": self.average_amount,
            "vs_average_pct": self.vs_average,
            "trend": self.trend,
            "rank": self.rank,
            "recommendations": self.recommendations,
        }


@dataclass
class ExpenseInsightsReport:
    """Comprehensive expense insights report.
    
    Attributes:
        report_id: Unique report identifier
        generated_at: When report was generated (UTC)
        period_months: Number of months analyzed
        total_spending: Total spending in period
        average_monthly: Average monthly spending
        highest_category: Category with highest spending
        lowest_category: Category with lowest spending
        spending_patterns: Dict of category -> SpendingPattern
        anomalies: List of detected anomalies
        category_insights: List of category insights
        overall_trend: Overall spending trend (increasing/decreasing/stable)
        recommendations: List of high-level recommendations
        opportunities: List of potential savings opportunities
    """
    report_id: str
    generated_at: datetime
    period_months: int
    total_spending: float
    average_monthly: float
    highest_category: str
    lowest_category: str
    spending_patterns: dict[str, SpendingPattern]
    anomalies: list[SpendingAnomaly]
    category_insights: list[CategoryInsight]
    overall_trend: str
    recommendations: list[str]
    opportunities: list[dict]
    
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
            "period_months": self.period_months,
            "total_spending": self.total_spending,
            "average_monthly": self.average_monthly,
            "highest_category": self.highest_category,
            "lowest_category": self.lowest_category,
            "overall_trend": self.overall_trend,
            "anomalies": [
                {
                    "type": a.anomaly_type.value,
                    "category": a.category,
                    "amount": a.amount,
                    "severity": a.severity.value,
                    "message": a.message,
                }
                for a in self.anomalies
            ],
            "category_insights": [c.to_dict() for c in self.category_insights],
            "recommendations": self.recommendations,
            "opportunities": self.opportunities,
        }


class ExpenseAnalytics:
    """Engine for analyzing spending patterns and generating insights."""
    
    def __init__(self):
        """Initialize analytics engine."""
        self.spending_history: dict[str, list[tuple[datetime, float]]] = {}
        self.patterns: dict[str, SpendingPattern] = {}
    
    def add_transaction(self, category: str, amount: float, transaction_date: datetime):
        """Add a transaction for analysis.
        
        Args:
            category: Expense category
            amount: Transaction amount
            transaction_date: When transaction occurred
        """
        if category not in self.spending_history:
            self.spending_history[category] = []
        self.spending_history[category].append((transaction_date, amount))
    
    def analyze_spending_patterns(self) -> dict[str, SpendingPattern]:
        """Analyze spending patterns by category.
        
        Returns:
            Dictionary of category -> SpendingPattern
        """
        self.patterns = {}
        
        for category, transactions in self.spending_history.items():
            if not transactions:
                continue
            
            # Group by month and sum
            monthly_totals: dict[str, float] = {}
            for date, amount in transactions:
                month_key = date.strftime("%Y-%m")
                monthly_totals[month_key] = monthly_totals.get(month_key, 0) + amount
            
            monthly_amounts = list(monthly_totals.values())
            if not monthly_amounts:
                continue
            
            avg = statistics.mean(monthly_amounts)
            median = statistics.median(monthly_amounts)
            std_dev = statistics.stdev(monthly_amounts) if len(monthly_amounts) > 1 else 0.0
            
            # Calculate trend using simple linear regression
            trend_slope = self._calculate_trend(monthly_amounts)
            if trend_slope > 0.05:  # More than 5% monthly increase
                trend = "increasing"
            elif trend_slope < -0.05:  # More than 5% monthly decrease
                trend = "decreasing"
            else:
                trend = "stable"
            
            self.patterns[category] = SpendingPattern(
                category=category,
                monthly_amounts=monthly_amounts,
                average=avg,
                median=median,
                std_dev=std_dev,
                trend=trend,
                trend_slope=trend_slope,
            )
        
        return self.patterns
    
    def _calculate_trend(self, values: list[float]) -> float:
        """Calculate trend slope using simple linear regression."""
        if len(values) < 2:
            return 0.0
        
        n = len(values)
        x_vals = list(range(n))
        x_mean = sum(x_vals) / n
        y_mean = sum(values) / n
        
        numerator = sum((x_vals[i] - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((x_vals[i] - x_mean) ** 2 for i in range(n))
        
        if denominator == 0:
            return 0.0
        
        slope = numerator / denominator
        return slope / y_mean if y_mean > 0 else 0.0
    
    def detect_anomalies(self, threshold_std: float = 2.0) -> list[SpendingAnomaly]:
        """Detect spending anomalies using statistical methods.
        
        Args:
            threshold_std: Standard deviations for anomaly threshold
        
        Returns:
            List of detected anomalies
        """
        if not self.patterns:
            self.analyze_spending_patterns()
        
        anomalies: list[SpendingAnomaly] = []
        
        for category, pattern in self.patterns.items():
                if len(pattern.monthly_amounts) < 2:
                    continue
            
                # Calculate baseline from all but last month
                baseline_amounts = pattern.monthly_amounts[:-1]
                if len(baseline_amounts) > 0:
                    baseline_avg = sum(baseline_amounts) / len(baseline_amounts)
                    baseline_std = statistics.stdev(baseline_amounts) if len(baseline_amounts) > 1 else 0.0
                else:
                    baseline_avg = pattern.average
                    baseline_std = pattern.std_dev
            
                # Check most recent month against baseline
                recent_month = pattern.monthly_amounts[-1]
            
                if baseline_std == 0:
                    # All baseline values are the same, use a percentage threshold instead
                    if recent_month > baseline_avg * 1.5:  # 50% increase
                        severity = InsightSeverity.WARNING
                        anomaly_type = AnomalyType.UNUSUALLY_HIGH
                        message = f"Spending on {category} (${recent_month:.2f}) is 50%+ above baseline"
                    
                        anomalies.append(SpendingAnomaly(
                            anomaly_type=anomaly_type,
                            category=category,
                            amount=recent_month,
                            expected_range=(baseline_avg * 0.8, baseline_avg * 1.2),
                            severity=severity,
                            message=message,
                        ))
                else:
                    z_score = (recent_month - baseline_avg) / baseline_std
                
                    if abs(z_score) > threshold_std:
                        lower = baseline_avg - (threshold_std * baseline_std)
                        upper = baseline_avg + (threshold_std * baseline_std)
                    
                        if recent_month > upper:
                            severity = InsightSeverity.WARNING if z_score < 3 else InsightSeverity.CRITICAL
                            anomaly_type = AnomalyType.UNUSUALLY_HIGH
                            message = f"Spending on {category} (${recent_month:.2f}) is unusually high"
                        else:
                            severity = InsightSeverity.NOTICE
                            anomaly_type = AnomalyType.UNUSUALLY_LOW
                            message = f"Spending on {category} (${recent_month:.2f}) is unusually low"
                    
                        anomalies.append(SpendingAnomaly(
                            anomaly_type=anomaly_type,
                            category=category,
                            amount=recent_month,
                            expected_range=(lower, upper),
                            severity=severity,
                            message=message,
                        ))
        
        return anomalies
    
    def get_category_insights(self) -> list[CategoryInsight]:
        """Generate insights for each spending category.
        
        Returns:
            List of CategoryInsight objects
        """
        if not self.patterns:
            self.analyze_spending_patterns()
        
        insights: list[CategoryInsight] = []
        
        # Get current month spending
        current_month = datetime.now(timezone.utc).strftime("%Y-%m")
        current_amounts: dict[str, float] = {}
        
        for category, transactions in self.spending_history.items():
            total = sum(amount for date, amount in transactions
                       if date.strftime("%Y-%m") == current_month)
            if total > 0:
                current_amounts[category] = total
        
        # Sort by amount for ranking
        sorted_cats = sorted(current_amounts.items(), key=lambda x: x[1], reverse=True)
        
        for rank, (category, current) in enumerate(sorted_cats, 1):
            pattern = self.patterns.get(category)
            if not pattern:
                continue
            
            vs_avg = ((current - pattern.average) / pattern.average * 100) if pattern.average > 0 else 0
            
            recommendations = []
            if vs_avg > 20:
                recommendations.append(f"Spending is {abs(vs_avg):.0f}% above average - review budget")
            elif pattern.trend == "increasing":
                recommendations.append("Spending trend is increasing - monitor closely")
            
            insights.append(CategoryInsight(
                category=category,
                current_amount=current,
                average_amount=pattern.average,
                vs_average=vs_avg,
                trend=pattern.trend,
                rank=rank,
                recommendations=recommendations,
            ))
        
        return insights
    
    def generate_insights_report(self) -> ExpenseInsightsReport:
        """Generate comprehensive insights report.
        
        Returns:
            ExpenseInsightsReport with all analysis
        """
        patterns = self.analyze_spending_patterns()
        anomalies = self.detect_anomalies()
        category_insights = self.get_category_insights()
        
        # Calculate totals
        total_spending = sum(pattern.average * len(pattern.monthly_amounts)
                            for pattern in patterns.values())
        period_months = max(len(p.monthly_amounts) for p in patterns.values()) if patterns else 0
        avg_monthly = total_spending / period_months if period_months > 0 else 0
        
        # Find highest and lowest
        highest_cat = max(patterns.keys(), key=lambda k: patterns[k].average) if patterns else "N/A"
        lowest_cat = min(patterns.keys(), key=lambda k: patterns[k].average) if patterns else "N/A"
        
        # Overall trend
        all_trends = [p.trend for p in patterns.values()]
        if all_trends.count("increasing") > len(all_trends) / 2:
            overall_trend = "increasing"
        elif all_trends.count("decreasing") > len(all_trends) / 2:
            overall_trend = "decreasing"
        else:
            overall_trend = "stable"
        
        # Generate recommendations
        recommendations = []
        if overall_trend == "increasing":
            recommendations.append("Overall spending is increasing - implement budget controls")
        
        critical_anomalies = [a for a in anomalies if a.severity == InsightSeverity.CRITICAL]
        if critical_anomalies:
            recommendations.append(f"Address {len(critical_anomalies)} critical spending anomalies")
        
        # Find savings opportunities
        opportunities = []
        for insight in sorted(category_insights, key=lambda x: x.rank)[:3]:
            if insight.vs_average > 15:
                savings = insight.current_amount - insight.average_amount
                opportunities.append({
                    "category": insight.category,
                    "current": insight.current_amount,
                    "potential_savings": savings,
                    "reason": "Above average spending",
                })
        
        return ExpenseInsightsReport(
            report_id=str(uuid.uuid4()),
            generated_at=datetime.now(timezone.utc),
            period_months=period_months,
            total_spending=total_spending,
            average_monthly=avg_monthly,
            highest_category=highest_cat,
            lowest_category=lowest_cat,
            spending_patterns=patterns,
            anomalies=anomalies,
            category_insights=category_insights,
            overall_trend=overall_trend,
            recommendations=recommendations,
            opportunities=opportunities,
        )
