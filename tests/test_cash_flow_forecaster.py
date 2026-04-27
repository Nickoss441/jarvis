"""Tests for financial cash flow forecasting."""

import pytest
from datetime import datetime, timezone, timedelta

from jarvis.tools.cash_flow_forecaster import (
    CashFlowType, ForecastPeriod, CashFlowTrend,
    CashFlowEntry, MonthlyMetrics, CashFlowForecast,
    RunwayAnalysis, CashFlowForecaster
)


class TestCashFlowType:
    """Tests for cash flow types."""
    
    def test_all_types(self):
        """Verify all types are defined."""
        types = [t.value for t in CashFlowType]
        assert "income" in types
        assert "expense" in types
        assert "investment" in types


class TestForecastPeriod:
    """Tests for forecast periods."""
    
    def test_all_periods(self):
        """Verify all periods are defined."""
        periods = [p.value for p in ForecastPeriod]
        assert "weekly" in periods
        assert "monthly" in periods
        assert "quarterly" in periods
        assert "annual" in periods


class TestCashFlowEntry:
    """Tests for cash flow entries."""
    
    def test_entry_creation(self):
        """Test creating a cash flow entry."""
        now = datetime.now(timezone.utc)
        entry = CashFlowEntry(
            entry_id="e-1",
            amount=1500.0,
            flow_type=CashFlowType.INCOME,
            date=now,
            category="Salary",
            description="Monthly salary",
        )
        assert entry.amount == 1500.0
        assert entry.flow_type == CashFlowType.INCOME
    
    def test_entry_naive_datetime_raises(self):
        """Test that naive datetime raises error."""
        naive = datetime(2026, 5, 27, 10, 0, 0)
        with pytest.raises(ValueError, match="timezone-aware"):
            CashFlowEntry(
                entry_id="e-1",
                amount=100.0,
                flow_type=CashFlowType.EXPENSE,
                date=naive,
                category="Test",
            )


class TestMonthlyMetrics:
    """Tests for monthly metrics."""
    
    def test_metrics_creation(self):
        """Test creating monthly metrics."""
        metrics = MonthlyMetrics(
            year=2026,
            month=5,
            total_inflow=5000.0,
            total_outflow=3000.0,
            net_flow=2000.0,
            expense_count=15,
            income_count=1,
        )
        assert metrics.net_flow == 2000.0
    
    def test_savings_rate(self):
        """Test savings rate calculation."""
        metrics = MonthlyMetrics(
            year=2026,
            month=5,
            total_inflow=5000.0,
            total_outflow=3000.0,
            net_flow=2000.0,
            expense_count=10,
            income_count=1,
        )
        assert metrics.savings_rate == pytest.approx(40.0)
    
    def test_savings_rate_zero_inflow(self):
        """Test savings rate with zero inflow."""
        metrics = MonthlyMetrics(
            year=2026,
            month=5,
            total_inflow=0.0,
            total_outflow=0.0,
            net_flow=0.0,
            expense_count=0,
            income_count=0,
        )
        assert metrics.savings_rate == 0


class TestCashFlowForecast:
    """Tests for cash flow forecasts."""
    
    def test_forecast_creation(self):
        """Test creating a forecast."""
        now = datetime.now(timezone.utc)
        forecast = CashFlowForecast(
            forecast_id="f-1",
            period_start=now,
            period_end=now + timedelta(days=90),
            forecasted_inflow=15000.0,
            forecasted_outflow=9000.0,
            forecasted_net=6000.0,
            confidence=75,
            assumptions=["Based on historical data"],
        )
        assert forecast.confidence == 75
        assert forecast.forecasted_net == 6000.0
    
    def test_forecast_invalid_confidence_raises(self):
        """Test that invalid confidence raises error."""
        now = datetime.now(timezone.utc)
        with pytest.raises(ValueError, match="Confidence"):
            CashFlowForecast(
                forecast_id="f-1",
                period_start=now,
                period_end=now + timedelta(days=90),
                forecasted_inflow=1000.0,
                forecasted_outflow=500.0,
                forecasted_net=500.0,
                confidence=150,  # Invalid
            )


class TestRunwayAnalysis:
    """Tests for runway analysis."""
    
    def test_analysis_creation(self):
        """Test creating runway analysis."""
        now = datetime.now(timezone.utc)
        analysis = RunwayAnalysis(
            analysis_id="r-1",
            current_balance=50000.0,
            monthly_burn_rate=2000.0,
            runway_months=25,
            depletion_date=now + timedelta(days=750),
            status="healthy",
            recommendations=["Good position"],
        )
        assert analysis.current_balance == 50000.0
        assert analysis.status == "healthy"


class TestCashFlowForecaster:
    """Tests for cash flow forecaster."""
    
    def test_forecaster_creation(self):
        """Test creating forecaster."""
        forecaster = CashFlowForecaster()
        assert len(forecaster.entries) == 0
    
    def test_add_entry(self):
        """Test adding a cash flow entry."""
        forecaster = CashFlowForecaster()
        now = datetime.now(timezone.utc)
        
        entry = forecaster.add_entry(
            amount=1500.0,
            flow_type=CashFlowType.INCOME,
            date=now,
            category="Salary",
            description="Monthly salary",
        )
        
        assert len(forecaster.entries) == 1
        assert entry.amount == 1500.0
    
    def test_set_current_balance(self):
        """Test setting current balance."""
        forecaster = CashFlowForecaster()
        forecaster.set_current_balance(25000.0)
        assert forecaster.current_balance == 25000.0
    
    def test_add_multiple_entries(self):
        """Test adding multiple entries."""
        forecaster = CashFlowForecaster()
        now = datetime.now(timezone.utc)
        
        forecaster.add_entry(
            amount=5000.0,
            flow_type=CashFlowType.INCOME,
            date=now,
            category="Salary",
        )
        
        forecaster.add_entry(
            amount=-1000.0,
            flow_type=CashFlowType.EXPENSE,
            date=now,
            category="Rent",
        )
        
        assert len(forecaster.entries) == 2
    
    def test_get_entries_for_period(self):
        """Test getting entries for a period."""
        forecaster = CashFlowForecaster()
        now = datetime.now(timezone.utc)
        
        # Add entry
        forecaster.add_entry(
            amount=1500.0,
            flow_type=CashFlowType.INCOME,
            date=now,
            category="Salary",
        )
        
        # Get entries for period
        entries = forecaster.get_entries_for_period(
            now - timedelta(days=1),
            now + timedelta(days=1),
        )
        
        assert len(entries) == 1
    
    def test_get_entries_for_period_empty(self):
        """Test getting entries for period with no entries."""
        forecaster = CashFlowForecaster()
        now = datetime.now(timezone.utc)
        
        entries = forecaster.get_entries_for_period(
            now - timedelta(days=1),
            now + timedelta(days=1),
        )
        
        assert len(entries) == 0
    
    def test_calculate_monthly_metrics(self):
        """Test calculating monthly metrics."""
        forecaster = CashFlowForecaster()
        now = datetime.now(timezone.utc)
        
        # Add entries for current month
        forecaster.add_entry(
            amount=5000.0,
            flow_type=CashFlowType.INCOME,
            date=now,
            category="Salary",
        )
        
        forecaster.add_entry(
            amount=-1000.0,
            flow_type=CashFlowType.EXPENSE,
            date=now,
            category="Rent",
        )
        
        metrics = forecaster.calculate_monthly_metrics(now.year, now.month)
        
        assert metrics.total_inflow == 5000.0
        assert metrics.total_outflow == 1000.0
        assert metrics.net_flow == 4000.0
    
    def test_analyze_trends(self):
        """Test trend analysis."""
        forecaster = CashFlowForecaster()
        now = datetime.now(timezone.utc)
        
        # Add consistent entries
        for i in range(5):
            date = now - timedelta(days=30 * i)
            forecaster.add_entry(
                amount=5000.0,
                flow_type=CashFlowType.INCOME,
                date=date,
                category="Salary",
            )
        
        trend = forecaster.analyze_trends()
        assert isinstance(trend, CashFlowTrend)
    
    def test_forecast_cash_flow(self):
        """Test forecasting cash flow."""
        forecaster = CashFlowForecaster()
        now = datetime.now(timezone.utc)
        
        # Add historical entries
        for i in range(6):
            date = now - timedelta(days=30 * i)
            forecaster.add_entry(
                amount=5000.0,
                flow_type=CashFlowType.INCOME,
                date=date,
                category="Salary",
            )
            forecaster.add_entry(
                amount=-2000.0,
                flow_type=CashFlowType.EXPENSE,
                date=date,
                category="Living",
            )
        
        forecast = forecaster.forecast_cash_flow(periods_ahead=3)
        
        assert isinstance(forecast, CashFlowForecast)
        assert forecast.confidence > 0
    
    def test_analyze_runway(self):
        """Test runway analysis."""
        forecaster = CashFlowForecaster()
        forecaster.set_current_balance(50000.0)
        now = datetime.now(timezone.utc)
        
        # Add consistent monthly burn
        for i in range(3):
            date = now - timedelta(days=30 * i)
            forecaster.add_entry(
                amount=-2000.0,
                flow_type=CashFlowType.EXPENSE,
                date=date,
                category="Living",
            )
        
        analysis = forecaster.analyze_runway()
        
        assert isinstance(analysis, RunwayAnalysis)
        assert analysis.current_balance == 50000.0


class TestCashFlowForecasterEdgeCases:
    """Edge case tests for cash flow forecaster."""
    
    def test_empty_forecaster_trend(self):
        """Test trend analysis on empty forecaster."""
        forecaster = CashFlowForecaster()
        trend = forecaster.analyze_trends()
        assert trend == CashFlowTrend.STABLE
    
    def test_single_entry_metrics(self):
        """Test metrics with single entry."""
        forecaster = CashFlowForecaster()
        now = datetime.now(timezone.utc)
        
        forecaster.add_entry(
            amount=1000.0,
            flow_type=CashFlowType.INCOME,
            date=now,
            category="Bonus",
        )
        
        metrics = forecaster.calculate_monthly_metrics(now.year, now.month)
        assert metrics.total_inflow == 1000.0
    
    def test_runway_with_positive_flow(self):
        """Test runway with positive cash flow."""
        forecaster = CashFlowForecaster()
        forecaster.set_current_balance(50000.0)
        now = datetime.now(timezone.utc)
        
        # Add positive flows (no burn)
        for i in range(3):
            date = now - timedelta(days=30 * i)
            forecaster.add_entry(
                amount=5000.0,
                flow_type=CashFlowType.INCOME,
                date=date,
                category="Salary",
            )
        
        analysis = forecaster.analyze_runway()
        assert analysis.status == "healthy"
    
    def test_forecast_with_no_historical_data(self):
        """Test forecast with no historical data."""
        forecaster = CashFlowForecaster()
        forecast = forecaster.forecast_cash_flow()
        
        assert isinstance(forecast, CashFlowForecast)
        assert forecast.forecasted_inflow == 0.0
    
    def test_multiple_categories(self):
        """Test tracking multiple categories."""
        forecaster = CashFlowForecaster()
        now = datetime.now(timezone.utc)
        
        forecaster.add_entry(
            amount=5000.0,
            flow_type=CashFlowType.INCOME,
            date=now,
            category="Salary",
        )
        
        forecaster.add_entry(
            amount=500.0,
            flow_type=CashFlowType.INCOME,
            date=now,
            category="Freelance",
        )
        
        forecaster.add_entry(
            amount=-1000.0,
            flow_type=CashFlowType.EXPENSE,
            date=now,
            category="Rent",
        )
        
        forecaster.add_entry(
            amount=-500.0,
            flow_type=CashFlowType.EXPENSE,
            date=now,
            category="Food",
        )
        
        assert len(forecaster.entries) == 4
