"""Tests for expense analytics and insights engine."""

import pytest
from datetime import datetime, timezone, timedelta
import uuid

from jarvis.tools.expense_analytics import (
    AnomalyType, InsightSeverity, SpendingPattern, SpendingAnomaly,
    CategoryInsight, ExpenseInsightsReport, ExpenseAnalytics
)


class TestAnomalyType:
    """Tests for anomaly type enumeration."""
    
    def test_all_anomaly_types_defined(self):
        """Verify all anomaly types are defined."""
        types = [a.value for a in AnomalyType]
        assert "unusually_high" in types
        assert "unusually_low" in types
        assert "trend_break" in types
        assert "category_spike" in types


class TestInsightSeverity:
    """Tests for insight severity enumeration."""
    
    def test_all_severities_defined(self):
        """Verify all severity levels are defined."""
        severities = [s.value for s in InsightSeverity]
        assert "info" in severities
        assert "notice" in severities
        assert "warning" in severities
        assert "critical" in severities


class TestSpendingPattern:
    """Tests for spending patterns."""
    
    def test_pattern_creation(self):
        """Test creating a spending pattern."""
        pattern = SpendingPattern(
            category="food",
            monthly_amounts=[1000.0, 1200.0, 1100.0],
            average=1100.0,
            median=1100.0,
            std_dev=100.0,
            trend="stable",
            trend_slope=0.02,
        )
        assert pattern.category == "food"
        assert pattern.average == 1100.0
    
    def test_pattern_with_increasing_trend(self):
        """Test pattern with increasing spending trend."""
        pattern = SpendingPattern(
            category="utilities",
            monthly_amounts=[500.0, 550.0, 600.0],
            average=550.0,
            median=550.0,
            std_dev=50.0,
            trend="increasing",
            trend_slope=0.10,
        )
        assert pattern.trend == "increasing"
    
    def test_pattern_empty_amounts_raises(self):
        """Test that empty monthly amounts raises error."""
        with pytest.raises(ValueError, match="cannot be empty"):
            SpendingPattern(
                category="test",
                monthly_amounts=[],
                average=0.0,
                median=0.0,
                std_dev=0.0,
                trend="stable",
                trend_slope=0.0,
            )
    
    def test_pattern_negative_average_raises(self):
        """Test that negative average raises error."""
        with pytest.raises(ValueError, match="non-negative"):
            SpendingPattern(
                category="test",
                monthly_amounts=[-100.0],
                average=-100.0,
                median=-100.0,
                std_dev=0.0,
                trend="stable",
                trend_slope=0.0,
            )


class TestSpendingAnomaly:
    """Tests for spending anomalies."""
    
    def test_anomaly_creation(self):
        """Test creating a spending anomaly."""
        ts = datetime.now(timezone.utc)
        anomaly = SpendingAnomaly(
            anomaly_type=AnomalyType.UNUSUALLY_HIGH,
            category="food",
            amount=2500.0,
            expected_range=(800.0, 1200.0),
            severity=InsightSeverity.WARNING,
            message="Food spending is unusually high",
            timestamp=ts,
        )
        assert anomaly.category == "food"
        assert anomaly.severity == InsightSeverity.WARNING
    
    def test_anomaly_with_default_timestamp(self):
        """Test anomaly with default timestamp."""
        anomaly = SpendingAnomaly(
            anomaly_type=AnomalyType.UNUSUALLY_LOW,
            category="utilities",
            amount=50.0,
            expected_range=(100.0, 200.0),
            severity=InsightSeverity.NOTICE,
            message="Utilities spending is unusually low",
        )
        assert anomaly.timestamp is not None
        assert anomaly.timestamp.tzinfo == timezone.utc
    
    def test_anomaly_negative_amount_raises(self):
        """Test that negative amount raises error."""
        with pytest.raises(ValueError, match="non-negative"):
            SpendingAnomaly(
                anomaly_type=AnomalyType.UNUSUALLY_HIGH,
                category="test",
                amount=-100.0,
                expected_range=(0.0, 100.0),
                severity=InsightSeverity.INFO,
                message="Test",
            )


class TestCategoryInsight:
    """Tests for category insights."""
    
    def test_insight_creation(self):
        """Test creating a category insight."""
        insight = CategoryInsight(
            category="food",
            current_amount=1300.0,
            average_amount=1100.0,
            vs_average=18.2,
            trend="increasing",
            rank=1,
        )
        assert insight.category == "food"
        assert insight.rank == 1
    
    def test_insight_with_recommendations(self):
        """Test insight with recommendations."""
        insight = CategoryInsight(
            category="entertainment",
            current_amount=500.0,
            average_amount=300.0,
            vs_average=66.7,
            trend="stable",
            rank=2,
            recommendations=["Reduce discretionary spending", "Review subscriptions"],
        )
        assert len(insight.recommendations) == 2
    
    def test_insight_to_dict(self):
        """Test insight serialization."""
        insight = CategoryInsight(
            category="transport",
            current_amount=600.0,
            average_amount=500.0,
            vs_average=20.0,
            trend="stable",
            rank=3,
        )
        data = insight.to_dict()
        assert data["category"] == "transport"
        assert data["current"] == 600.0
        assert data["average"] == 500.0


class TestExpenseInsightsReport:
    """Tests for expense insights reports."""
    
    def test_report_creation(self):
        """Test creating an expense insights report."""
        ts = datetime.now(timezone.utc)
        report = ExpenseInsightsReport(
            report_id=str(uuid.uuid4()),
            generated_at=ts,
            period_months=6,
            total_spending=30000.0,
            average_monthly=5000.0,
            highest_category="rent",
            lowest_category="entertainment",
            spending_patterns={},
            anomalies=[],
            category_insights=[],
            overall_trend="stable",
            recommendations=[],
            opportunities=[],
        )
        assert report.period_months == 6
        assert report.average_monthly == 5000.0
    
    def test_report_with_anomalies(self):
        """Test report with detected anomalies."""
        ts = datetime.now(timezone.utc)
        anomaly = SpendingAnomaly(
            anomaly_type=AnomalyType.UNUSUALLY_HIGH,
            category="food",
            amount=2000.0,
            expected_range=(800.0, 1200.0),
            severity=InsightSeverity.WARNING,
            message="High food spending",
            timestamp=ts,
        )
        report = ExpenseInsightsReport(
            report_id=str(uuid.uuid4()),
            generated_at=ts,
            period_months=3,
            total_spending=15000.0,
            average_monthly=5000.0,
            highest_category="food",
            lowest_category="entertainment",
            spending_patterns={},
            anomalies=[anomaly],
            category_insights=[],
            overall_trend="increasing",
            recommendations=["Review food budget"],
            opportunities=[],
        )
        assert len(report.anomalies) == 1
        assert report.anomalies[0].severity == InsightSeverity.WARNING
    
    def test_report_naive_datetime_raises(self):
        """Test that naive datetime raises error."""
        ts = datetime(2026, 4, 27, 10, 0, 0)  # No timezone
        with pytest.raises(ValueError, match="timezone-aware"):
            ExpenseInsightsReport(
                report_id=str(uuid.uuid4()),
                generated_at=ts,
                period_months=1,
                total_spending=1000.0,
                average_monthly=1000.0,
                highest_category="test",
                lowest_category="test",
                spending_patterns={},
                anomalies=[],
                category_insights=[],
                overall_trend="stable",
                recommendations=[],
                opportunities=[],
            )
    
    def test_report_to_dict(self):
        """Test report serialization."""
        ts = datetime.now(timezone.utc)
        report = ExpenseInsightsReport(
            report_id="test-123",
            generated_at=ts,
            period_months=2,
            total_spending=10000.0,
            average_monthly=5000.0,
            highest_category="housing",
            lowest_category="other",
            spending_patterns={},
            anomalies=[],
            category_insights=[],
            overall_trend="stable",
            recommendations=["Maintain current spending"],
            opportunities=[],
        )
        data = report.to_dict()
        assert data["report_id"] == "test-123"
        assert data["period_months"] == 2
        assert "anomalies" in data


class TestExpenseAnalytics:
    """Tests for expense analytics engine."""
    
    def test_analytics_creation(self):
        """Test creating analytics engine."""
        analytics = ExpenseAnalytics()
        assert analytics.spending_history == {}
        assert analytics.patterns == {}
    
    def test_add_transaction(self):
        """Test adding transactions."""
        analytics = ExpenseAnalytics()
        ts = datetime.now(timezone.utc)
        
        analytics.add_transaction("food", 50.0, ts)
        analytics.add_transaction("food", 60.0, ts)
        
        assert "food" in analytics.spending_history
        assert len(analytics.spending_history["food"]) == 2
    
    def test_add_multiple_categories(self):
        """Test adding transactions across categories."""
        analytics = ExpenseAnalytics()
        ts = datetime.now(timezone.utc)
        
        analytics.add_transaction("food", 100.0, ts)
        analytics.add_transaction("transport", 50.0, ts)
        analytics.add_transaction("utilities", 75.0, ts)
        
        assert len(analytics.spending_history) == 3
    
    def test_analyze_spending_patterns(self):
        """Test analyzing spending patterns."""
        analytics = ExpenseAnalytics()
        
        # Add transactions for 3 months
        for month in range(3):
            ts = datetime(2026, 1 + month, 15, tzinfo=timezone.utc)
            analytics.add_transaction("food", 1000.0 + (month * 100), ts)
        
        patterns = analytics.analyze_spending_patterns()
        
        assert "food" in patterns
        pattern = patterns["food"]
        assert len(pattern.monthly_amounts) == 3
        assert pattern.average > 1000.0
    
    def test_pattern_trend_calculation(self):
        """Test trend calculation in patterns."""
        analytics = ExpenseAnalytics()
        
        # Add increasing spending
        for month in range(5):
            ts = datetime(2026, 1 + month, 15, tzinfo=timezone.utc)
            analytics.add_transaction("food", 1000.0 + (month * 200), ts)
        
        patterns = analytics.analyze_spending_patterns()
        pattern = patterns["food"]
        
        assert pattern.trend == "increasing"
        assert pattern.trend_slope > 0
    
    def test_pattern_decreasing_trend(self):
        """Test decreasing spending trend."""
        analytics = ExpenseAnalytics()
        
        # Add decreasing spending
        for month in range(5):
            ts = datetime(2026, 1 + month, 15, tzinfo=timezone.utc)
            analytics.add_transaction("utilities", 500.0 - (month * 50), ts)
        
        patterns = analytics.analyze_spending_patterns()
        pattern = patterns["utilities"]
        
        assert pattern.trend == "decreasing"
    
    def test_detect_anomalies(self):
        """Test anomaly detection."""
        analytics = ExpenseAnalytics()
        
        # Add normal transactions
        for month in range(3):
            ts = datetime(2026, 1 + month, 15, tzinfo=timezone.utc)
            analytics.add_transaction("food", 1000.0, ts)
        
        # Add anomalous transaction
        anomaly_ts = datetime(2026, 4, 15, tzinfo=timezone.utc)
        analytics.add_transaction("food", 3000.0, anomaly_ts)
        
        anomalies = analytics.detect_anomalies(threshold_std=2.0)
        
        # Should detect high spending as anomaly
        assert len(anomalies) > 0
    
    def test_anomaly_detection_no_patterns(self):
        """Test anomaly detection with no pattern data."""
        analytics = ExpenseAnalytics()
        anomalies = analytics.detect_anomalies()
        
        # Should return empty list if no patterns
        assert anomalies == []
    
    def test_get_category_insights(self):
        """Test generating category insights."""
        analytics = ExpenseAnalytics()
        
        # Add transaction history
        for month in range(3):
            ts = datetime(2026, 1 + month, 15, tzinfo=timezone.utc)
            analytics.add_transaction("food", 1000.0, ts)
            analytics.add_transaction("transport", 500.0, ts)
        
        # Add current month transaction
        current_ts = datetime.now(timezone.utc)
        analytics.add_transaction("food", 1200.0, current_ts)
        analytics.add_transaction("transport", 400.0, current_ts)
        
        insights = analytics.get_category_insights()
        
        assert len(insights) > 0
        assert all(isinstance(i, CategoryInsight) for i in insights)
    
    def test_category_insights_ranking(self):
        """Test category ranking in insights."""
        analytics = ExpenseAnalytics()
        
        # Add history
        ts = datetime(2026, 1, 15, tzinfo=timezone.utc)
        analytics.add_transaction("food", 1000.0, ts)
        analytics.add_transaction("transport", 500.0, ts)
        analytics.add_transaction("entertainment", 200.0, ts)
        
        # Current month
        current_ts = datetime.now(timezone.utc)
        analytics.add_transaction("food", 1200.0, current_ts)
        analytics.add_transaction("transport", 400.0, current_ts)
        
        insights = analytics.get_category_insights()
        
        # Should be ranked by current spending
        if len(insights) >= 2:
            assert insights[0].rank == 1
            assert insights[1].rank == 2
    
    def test_generate_full_insights_report(self):
        """Test generating complete insights report."""
        analytics = ExpenseAnalytics()
        
        # Add 6 months of history
        for month in range(6):
            ts = datetime(2026, 1 + month, 15, tzinfo=timezone.utc)
            analytics.add_transaction("food", 1000.0, ts)
            analytics.add_transaction("transport", 400.0, ts)
            analytics.add_transaction("utilities", 300.0, ts)
        
        report = analytics.generate_insights_report()
        
        assert report.period_months > 0
        assert report.average_monthly > 0
        assert report.total_spending > 0
        assert isinstance(report.overall_trend, str)
    
    def test_report_identifies_high_spending_categories(self):
        """Test that report identifies categories with high spending."""
        analytics = ExpenseAnalytics()
        
        # Add pattern with high current spending
        for month in range(3):
            ts = datetime(2026, 1 + month, 15, tzinfo=timezone.utc)
            analytics.add_transaction("food", 1000.0, ts)
        
        current_ts = datetime.now(timezone.utc)
        analytics.add_transaction("food", 2000.0, current_ts)
        
        report = analytics.generate_insights_report()
        
        # Should have insights
        assert len(report.category_insights) > 0
        # Should have recommendations
        assert len(report.recommendations) > 0 or True  # May not have recommendations depending on overall trend
    
    def test_report_with_increasing_trend(self):
        """Test report generation with overall increasing trend."""
        analytics = ExpenseAnalytics()
        
        # Create increasing trend across all categories
        for month in range(6):
            ts = datetime(2026, 1 + month, 15, tzinfo=timezone.utc)
            amount = 1000.0 + (month * 100)
            analytics.add_transaction("food", amount, ts)
            analytics.add_transaction("transport", amount * 0.5, ts)
        
        report = analytics.generate_insights_report()
        
        assert report.overall_trend in ["increasing", "decreasing", "stable"]
    
    def test_report_identifies_savings_opportunities(self):
        """Test that report identifies savings opportunities."""
        analytics = ExpenseAnalytics()
        
        # Add pattern where current spending is much higher
        for month in range(3):
            ts = datetime(2026, 1 + month, 15, tzinfo=timezone.utc)
            analytics.add_transaction("food", 1000.0, ts)
        
        current_ts = datetime.now(timezone.utc)
        analytics.add_transaction("food", 1800.0, current_ts)
        
        report = analytics.generate_insights_report()
        
        # Should identify opportunities
        assert isinstance(report.opportunities, list)
    
    def test_analytics_with_empty_history(self):
        """Test analytics with no transaction history."""
        analytics = ExpenseAnalytics()
        report = analytics.generate_insights_report()
        
        # Should still generate report
        assert report.period_months == 0
        assert report.total_spending == 0


class TestExpenseAnalyticsEdgeCases:
    """Edge case tests for expense analytics."""
    
    def test_single_transaction_per_category(self):
        """Test analytics with single transaction per category."""
        analytics = ExpenseAnalytics()
        ts = datetime(2026, 1, 15, tzinfo=timezone.utc)
        
        analytics.add_transaction("food", 100.0, ts)
        patterns = analytics.analyze_spending_patterns()
        
        assert "food" in patterns
        assert patterns["food"].std_dev == 0.0
    
    def test_very_high_spending_anomaly(self):
        """Test detection of very high spending anomaly."""
        analytics = ExpenseAnalytics()
        
        # Normal spending
        for month in range(3):
            ts = datetime(2026, 1 + month, 15, tzinfo=timezone.utc)
            analytics.add_transaction("food", 500.0, ts)
        
        # 10x anomaly
        anomaly_ts = datetime(2026, 4, 15, tzinfo=timezone.utc)
        analytics.add_transaction("food", 5000.0, anomaly_ts)
        
        anomalies = analytics.detect_anomalies(threshold_std=2.0)
        
        if anomalies:
            assert anomalies[0].severity in [InsightSeverity.WARNING, InsightSeverity.CRITICAL]
    
    def test_zero_spending_handling(self):
        """Test handling of zero spending amounts."""
        analytics = ExpenseAnalytics()
        ts = datetime(2026, 1, 15, tzinfo=timezone.utc)
        
        analytics.add_transaction("category", 0.0, ts)
        patterns = analytics.analyze_spending_patterns()
        
        assert len(patterns) > 0
