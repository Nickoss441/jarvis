"""Tests for financial dashboard and reporting engine."""

import pytest
from datetime import datetime, timezone, timedelta
import uuid

from jarvis.tools.financial_dashboard import (
    ReportFormat, ReportPeriod, NetWorthSnapshot, SpendingAnalysis,
    AssetAllocation, FinancialMetrics, FinancialReport, DashboardBuilder
)


class TestReportFormat:
    """Tests for report format enumeration."""
    
    def test_all_formats_defined(self):
        """Verify all report formats are defined."""
        formats = [f.value for f in ReportFormat]
        assert "json" in formats
        assert "text" in formats
        assert "csv" in formats
        assert "html" in formats


class TestReportPeriod:
    """Tests for report period enumeration."""
    
    def test_all_periods_defined(self):
        """Verify all periods are defined."""
        periods = [p.value for p in ReportPeriod]
        assert "daily" in periods
        assert "monthly" in periods
        assert "yearly" in periods


class TestNetWorthSnapshot:
    """Tests for net worth snapshots."""
    
    def test_snapshot_creation(self):
        """Test creating a net worth snapshot."""
        ts = datetime.now(timezone.utc)
        snapshot = NetWorthSnapshot(
            timestamp=ts,
            total_assets=100000.00,
            total_liabilities=20000.00,
            net_worth=80000.00,
        )
        assert snapshot.net_worth == 80000.00
    
    def test_snapshot_with_breakdown(self):
        """Test snapshot with asset breakdown."""
        ts = datetime.now(timezone.utc)
        snapshot = NetWorthSnapshot(
            timestamp=ts,
            total_assets=100000.00,
            total_liabilities=0.0,
            net_worth=100000.00,
            breakdown={"cash": 50000.00, "crypto": 50000.00},
        )
        assert snapshot.breakdown["cash"] == 50000.00
    
    def test_snapshot_naive_datetime_raises(self):
        """Test that naive datetime raises error."""
        ts = datetime(2026, 4, 27, 10, 0, 0)  # No timezone
        with pytest.raises(ValueError, match="timezone-aware"):
            NetWorthSnapshot(
                timestamp=ts,
                total_assets=100000.00,
                total_liabilities=0.0,
                net_worth=100000.00,
            )


class TestSpendingAnalysis:
    """Tests for spending analysis."""
    
    def test_spending_analysis_creation(self):
        """Test creating spending analysis."""
        analysis = SpendingAnalysis(
            period="monthly",
            total_spending=5000.00,
            by_category={"food": 1000.00, "transport": 500.00},
            daily_average=166.67,
        )
        assert analysis.total_spending == 5000.00
        assert analysis.daily_average == pytest.approx(166.67, 0.1)
    
    def test_spending_with_top_categories(self):
        """Test spending analysis with top categories."""
        analysis = SpendingAnalysis(
            period="monthly",
            total_spending=3000.00,
            by_category={
                "food": 1200.00,
                "transport": 800.00,
                "entertainment": 500.00,
                "utilities": 300.00,
                "other": 200.00,
            },
            daily_average=100.0,
            top_categories=[
                ("food", 1200.00),
                ("transport", 800.00),
                ("entertainment", 500.00),
            ],
        )
        assert len(analysis.top_categories) == 3
        assert analysis.top_categories[0][0] == "food"


class TestAssetAllocation:
    """Tests for asset allocation."""
    
    def test_allocation_creation(self):
        """Test creating asset allocation."""
        allocation = AssetAllocation(
            cash=50.0,
            stocks=20.0,
            crypto=15.0,
            real_estate=10.0,
            bonds=5.0,
            other=0.0,
            total_value=100000.00,
        )
        assert allocation.cash == 50.0
        assert allocation.crypto == 15.0
    
    def test_allocation_sums_to_100(self):
        """Test that allocation percentages sum to 100%."""
        allocation = AssetAllocation(
            cash=40.0,
            stocks=30.0,
            crypto=20.0,
            real_estate=10.0,
            bonds=0.0,
            other=0.0,
            total_value=500000.00,
        )
        total = (allocation.cash + allocation.stocks + allocation.crypto +
                allocation.real_estate + allocation.bonds + allocation.other)
        assert total == 100.0
    
    def test_allocation_not_summing_to_100_raises(self):
        """Test that allocation not summing to 100% raises error."""
        with pytest.raises(ValueError, match="must sum to 100%"):
            AssetAllocation(
                cash=50.0,
                stocks=30.0,
                crypto=15.0,
                real_estate=0.0,
                bonds=0.0,
                other=0.0,
                total_value=100000.00,
            )


class TestFinancialMetrics:
    """Tests for financial metrics."""
    
    def test_metrics_creation(self):
        """Test creating financial metrics."""
        metrics = FinancialMetrics(
            net_worth=250000.00,
            savings_rate=25.0,
            expense_ratio=75.0,
            emergency_fund_months=6.0,
            debt_to_income=0.2,
            investment_return_ytd=12.5,
            cash_flow=2000.00,
        )
        assert metrics.net_worth == 250000.00
        assert metrics.savings_rate == 25.0
    
    def test_metrics_to_dict(self):
        """Test metrics serialization."""
        metrics = FinancialMetrics(
            net_worth=100000.00,
            savings_rate=20.0,
            expense_ratio=80.0,
            emergency_fund_months=3.0,
            debt_to_income=0.0,
            investment_return_ytd=5.0,
            cash_flow=1000.00,
        )
        data = metrics.to_dict()
        assert data["savings_rate"] == 20.0
        assert data["emergency_fund_months"] == 3.0


class TestFinancialReport:
    """Tests for financial reports."""
    
    def test_report_creation(self):
        """Test creating a financial report."""
        ts = datetime.now(timezone.utc)
        net_worth = NetWorthSnapshot(
            timestamp=ts,
            total_assets=100000.00,
            total_liabilities=0.0,
            net_worth=100000.00,
        )
        spending = SpendingAnalysis(
            period="monthly",
            total_spending=3000.00,
            by_category={"food": 1000.00},
            daily_average=100.0,
        )
        allocation = AssetAllocation(
            cash=100.0,
            stocks=0.0,
            crypto=0.0,
            real_estate=0.0,
            bonds=0.0,
            other=0.0,
            total_value=100000.00,
        )
        metrics = FinancialMetrics(
            net_worth=100000.00,
            savings_rate=25.0,
            expense_ratio=75.0,
            emergency_fund_months=33.3,
            debt_to_income=0.0,
            investment_return_ytd=0.0,
            cash_flow=1000.00,
        )
        
        report = FinancialReport(
            report_id=str(uuid.uuid4()),
            generated_at=ts,
            period=ReportPeriod.MONTHLY,
            net_worth_snapshot=net_worth,
            spending_analysis=spending,
            asset_allocation=allocation,
            metrics=metrics,
        )
        
        assert report.period == ReportPeriod.MONTHLY
        assert report.net_worth_snapshot.net_worth == 100000.00
    
    def test_report_to_json(self):
        """Test report JSON serialization."""
        ts = datetime.now(timezone.utc)
        net_worth = NetWorthSnapshot(
            timestamp=ts,
            total_assets=50000.00,
            total_liabilities=10000.00,
            net_worth=40000.00,
        )
        spending = SpendingAnalysis(
            period="monthly",
            total_spending=2000.00,
            by_category={},
            daily_average=66.67,
        )
        allocation = AssetAllocation(
            cash=100.0, stocks=0.0, crypto=0.0, real_estate=0.0,
            bonds=0.0, other=0.0, total_value=50000.00,
        )
        metrics = FinancialMetrics(
            net_worth=40000.00, savings_rate=20.0, expense_ratio=80.0,
            emergency_fund_months=20.0, debt_to_income=0.25,
            investment_return_ytd=0.0, cash_flow=500.00,
        )
        
        report = FinancialReport(
            report_id=str(uuid.uuid4()),
            generated_at=ts,
            period=ReportPeriod.MONTHLY,
            net_worth_snapshot=net_worth,
            spending_analysis=spending,
            asset_allocation=allocation,
            metrics=metrics,
        )
        
        json_str = report.to_json()
        assert isinstance(json_str, str)
        assert "net_worth" in json_str
        assert "40000" in json_str
    
    def test_report_to_text(self):
        """Test report text serialization."""
        ts = datetime.now(timezone.utc)
        net_worth = NetWorthSnapshot(
            timestamp=ts,
            total_assets=100000.00,
            total_liabilities=0.0,
            net_worth=100000.00,
        )
        spending = SpendingAnalysis(
            period="monthly",
            total_spending=3000.00,
            by_category={"food": 1500.00, "transport": 1000.00, "other": 500.00},
            daily_average=100.0,
            top_categories=[("food", 1500.00), ("transport", 1000.00)],
        )
        allocation = AssetAllocation(
            cash=100.0, stocks=0.0, crypto=0.0, real_estate=0.0,
            bonds=0.0, other=0.0, total_value=100000.00,
        )
        metrics = FinancialMetrics(
            net_worth=100000.00, savings_rate=30.0, expense_ratio=70.0,
            emergency_fund_months=33.3, debt_to_income=0.0,
            investment_return_ytd=0.0, cash_flow=3000.00,
        )
        
        report = FinancialReport(
            report_id=str(uuid.uuid4()),
            generated_at=ts,
            period=ReportPeriod.MONTHLY,
            net_worth_snapshot=net_worth,
            spending_analysis=spending,
            asset_allocation=allocation,
            metrics=metrics,
            recommendations=["Increase savings rate to 35%"],
        )
        
        text = report.to_text()
        assert isinstance(text, str)
        assert "NET WORTH SUMMARY" in text
        assert "FINANCIAL REPORT" in text
        assert "Increase savings rate" in text
    
    def test_report_to_csv(self):
        """Test report CSV serialization."""
        ts = datetime.now(timezone.utc)
        net_worth = NetWorthSnapshot(
            timestamp=ts,
            total_assets=100000.00,
            total_liabilities=10000.00,
            net_worth=90000.00,
        )
        spending = SpendingAnalysis(
            period="monthly",
            total_spending=3000.00,
            by_category={"food": 1500.00, "transport": 1500.00},
            daily_average=100.0,
        )
        allocation = AssetAllocation(
            cash=70.0, stocks=0.0, crypto=30.0, real_estate=0.0,
            bonds=0.0, other=0.0, total_value=100000.00,
        )
        metrics = FinancialMetrics(
            net_worth=90000.00, savings_rate=25.0, expense_ratio=75.0,
            emergency_fund_months=30.0, debt_to_income=0.11,
            investment_return_ytd=5.0, cash_flow=1000.00,
        )
        
        report = FinancialReport(
            report_id=str(uuid.uuid4()),
            generated_at=ts,
            period=ReportPeriod.MONTHLY,
            net_worth_snapshot=net_worth,
            spending_analysis=spending,
            asset_allocation=allocation,
            metrics=metrics,
        )
        
        csv = report.to_csv()
        assert isinstance(csv, str)
        assert "FINANCIAL SUMMARY" in csv
        assert "Net Worth,90000" in csv
        assert "food,1500" in csv


class TestDashboardBuilder:
    """Tests for dashboard builder."""
    
    def test_builder_creation(self):
        """Test creating a dashboard builder."""
        builder = DashboardBuilder()
        assert builder.wallet_data is None
        assert builder.income == 0.0
    
    def test_builder_fluent_interface(self):
        """Test builder fluent interface."""
        builder = DashboardBuilder()
        result = builder.set_income(5000.0)
        assert result is builder  # Should return self for chaining
    
    def test_builder_with_wallet_data(self):
        """Test builder with wallet data."""
        builder = DashboardBuilder()
        wallet = {
            "total_balance": 25000.00,
            "monthly_spending": 3000.00,
            "by_category": {"food": 1000.00, "transport": 500.00}
        }
        builder.add_wallet(wallet).set_income(5000.00)
        
        assert builder.wallet_data == wallet
        assert builder.income == 5000.00
    
    def test_builder_with_crypto_data(self):
        """Test builder with crypto data."""
        builder = DashboardBuilder()
        crypto = {
            "total_current_value": 15000.00,
            "pnl_percentage": 25.0,
            "rebalancing_needed": False,
        }
        builder.add_crypto(crypto)
        
        assert builder.crypto_data == crypto
    
    def test_calculate_net_worth(self):
        """Test net worth calculation."""
        builder = DashboardBuilder()
        builder.add_wallet({"total_balance": 25000.00}).add_crypto({"total_current_value": 15000.00})
        
        snapshot = builder.calculate_net_worth()
        assert snapshot.net_worth == 40000.00
        assert snapshot.total_assets == 40000.00
    
    def test_calculate_allocation(self):
        """Test allocation calculation."""
        builder = DashboardBuilder()
        builder.add_wallet({"total_balance": 25000.00}).add_crypto({"total_current_value": 25000.00})
        
        allocation = builder.calculate_allocation()
        assert allocation.cash == pytest.approx(50.0, 1)
        assert allocation.crypto == pytest.approx(50.0, 1)
        assert allocation.total_value == 50000.00
    
    def test_build_report(self):
        """Test building a complete report."""
        builder = DashboardBuilder()
        builder.add_wallet({
            "total_balance": 25000.00,
            "monthly_spending": 2000.00,
            "by_category": {"food": 800.00, "transport": 600.00, "other": 600.00}
        }).add_crypto({
            "total_current_value": 15000.00,
            "pnl_percentage": 10.0,
            "rebalancing_needed": True,  # Trigger rebalancing recommendation
        }).set_income(5000.00)
        
        report = builder.build(ReportPeriod.MONTHLY)
        
        assert report.period == ReportPeriod.MONTHLY
        assert report.net_worth_snapshot.net_worth == 40000.00
        assert report.metrics.savings_rate == pytest.approx(60.0, 1)  # (5000-2000)/5000 * 100
        assert len(report.recommendations) > 0  # Should have rebalancing recommendation
    
    def test_build_with_expense_alert(self):
        """Test report building with expense warnings."""
        builder = DashboardBuilder()
        builder.add_wallet({
            "total_balance": 5000.00,
            "monthly_spending": 6000.00,
            "by_category": {}
        }).set_income(4000.00)
        
        report = builder.build()
        
        # Should have alert about expenses exceeding income
        assert len(report.alerts) > 0
        assert any("exceed" in alert.get("message", "").lower() for alert in report.alerts)
    
    def test_build_with_low_savings_rate(self):
        """Test report with low savings rate recommendation."""
        builder = DashboardBuilder()
        builder.add_wallet({
            "total_balance": 10000.00,
            "monthly_spending": 4500.00,
            "by_category": {}
        }).set_income(5000.00)
        
        report = builder.build()
        
        # Savings rate is 10%, should get recommendation
        assert report.metrics.savings_rate == 10.0
        assert any("20%" in rec for rec in report.recommendations)
    
    def test_negative_income_raises(self):
        """Test that negative income raises error."""
        builder = DashboardBuilder()
        with pytest.raises(ValueError, match="non-negative"):
            builder.set_income(-1000.0)
