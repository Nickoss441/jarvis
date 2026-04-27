"""Tests for budget forecasting and projections engine."""

import pytest
from datetime import datetime, timezone, timedelta
import uuid

from jarvis.tools.budget_forecast import (
    ForecastMethod, GoalType, MonthlySpendingData, SpendingForecast,
    FinancialGoal, BudgetForecaster, generate_financial_forecast
)


class TestForecastMethod:
    """Tests for forecast method enumeration."""
    
    def test_all_methods_defined(self):
        """Verify all forecast methods are defined."""
        methods = [m.value for m in ForecastMethod]
        assert "simple_average" in methods
        assert "weighted_average" in methods
        assert "trend" in methods
        assert "seasonal" in methods


class TestGoalType:
    """Tests for goal type enumeration."""
    
    def test_all_goal_types_defined(self):
        """Verify all goal types are defined."""
        types = [t.value for t in GoalType]
        assert "savings" in types
        assert "debt_payoff" in types
        assert "retirement" in types


class TestMonthlySpendingData:
    """Tests for monthly spending data."""
    
    def test_spending_data_creation(self):
        """Test creating spending data."""
        data = MonthlySpendingData(
            year=2026,
            month=4,
            total_spending=2000.00,
            by_category={"food": 500.00, "transport": 300.00},
        )
        assert data.year == 2026
        assert data.month == 4
        assert data.total_spending == 2000.00
    
    def test_invalid_month_raises(self):
        """Test that invalid month raises error."""
        with pytest.raises(ValueError, match="Month must be 1-12"):
            MonthlySpendingData(
                year=2026,
                month=13,
                total_spending=2000.00,
                by_category={},
            )
    
    def test_negative_spending_raises(self):
        """Test that negative spending raises error."""
        with pytest.raises(ValueError, match="non-negative"):
            MonthlySpendingData(
                year=2026,
                month=4,
                total_spending=-100.00,
                by_category={},
            )


class TestSpendingForecast:
    """Tests for spending forecast."""
    
    def test_forecast_creation(self):
        """Test creating a forecast."""
        forecast = SpendingForecast(
            year=2026,
            month=5,
            forecast_amount=2000.00,
            confidence=0.85,
            method=ForecastMethod.SIMPLE_AVERAGE,
        )
        assert forecast.month == 5
        assert forecast.confidence == 0.85
    
    def test_invalid_confidence_raises(self):
        """Test that confidence outside 0.0-1.0 raises error."""
        with pytest.raises(ValueError, match="Confidence must be 0.0-1.0"):
            SpendingForecast(
                year=2026,
                month=5,
                forecast_amount=2000.00,
                confidence=1.5,
                method=ForecastMethod.SIMPLE_AVERAGE,
            )


class TestFinancialGoal:
    """Tests for financial goals."""
    
    def test_goal_creation(self):
        """Test creating a financial goal."""
        deadline = datetime(2026, 12, 31, tzinfo=timezone.utc)
        created = datetime(2026, 1, 1, tzinfo=timezone.utc)
        
        goal = FinancialGoal(
            goal_id=str(uuid.uuid4()),
            name="Vacation Fund",
            goal_type=GoalType.VACATION,
            target_amount=5000.00,
            current_amount=1000.00,
            deadline=deadline,
            created_at=created,
        )
        assert goal.target_amount == 5000.00
        assert goal.current_amount == 1000.00
    
    def test_goal_progress_percent(self):
        """Test progress percentage calculation."""
        deadline = datetime.now(timezone.utc) + timedelta(days=365)
        created = datetime.now(timezone.utc)
        
        goal = FinancialGoal(
            goal_id=str(uuid.uuid4()),
            name="Test Goal",
            goal_type=GoalType.SAVINGS,
            target_amount=10000.00,
            current_amount=2500.00,
            deadline=deadline,
            created_at=created,
        )
        assert goal.progress_percent() == 25.0
    
    def test_remaining_amount(self):
        """Test remaining amount calculation."""
        deadline = datetime.now(timezone.utc) + timedelta(days=365)
        created = datetime.now(timezone.utc)
        
        goal = FinancialGoal(
            goal_id=str(uuid.uuid4()),
            name="Test Goal",
            goal_type=GoalType.SAVINGS,
            target_amount=10000.00,
            current_amount=6000.00,
            deadline=deadline,
            created_at=created,
        )
        assert goal.remaining_amount() == 4000.00
    
    def test_is_on_track(self):
        """Test on-track detection."""
        deadline = datetime.now(timezone.utc) + timedelta(days=90)  # 3 months
        created = datetime.now(timezone.utc)
        
        goal = FinancialGoal(
            goal_id=str(uuid.uuid4()),
            name="Test Goal",
            goal_type=GoalType.SAVINGS,
            target_amount=3000.00,
            current_amount=0.00,
            deadline=deadline,
            created_at=created,
        )
        
        # Need 3000/3 months = 1000/month, so monthly contribution of 1100 is on track
        # (higher to account for rounding in days_remaining / 30.0)
        assert goal.is_on_track(1100.0) is True
        assert goal.is_on_track(500.0) is False


class TestBudgetForecaster:
    """Tests for budget forecasting."""
    
    def test_forecaster_creation(self):
        """Test creating a forecaster."""
        forecaster = BudgetForecaster(min_data_points=3)
        assert forecaster.min_data_points == 3
        assert len(forecaster.spending_history) == 0
    
    def test_add_historical_data(self):
        """Test adding historical data."""
        forecaster = BudgetForecaster()
        data = MonthlySpendingData(
            year=2026,
            month=1,
            total_spending=2000.00,
            by_category={"food": 500.00},
        )
        forecaster.add_historical_data(data)
        assert len(forecaster.spending_history) == 1
    
    def test_add_duplicate_data_raises(self):
        """Test that duplicate data raises error."""
        forecaster = BudgetForecaster()
        data = MonthlySpendingData(
            year=2026,
            month=1,
            total_spending=2000.00,
            by_category={},
        )
        forecaster.add_historical_data(data)
        
        with pytest.raises(ValueError, match="already exists"):
            forecaster.add_historical_data(data)
    
    def test_forecast_simple_average(self):
        """Test simple average forecasting."""
        forecaster = BudgetForecaster(min_data_points=2)
        
        forecaster.add_historical_data(MonthlySpendingData(
            year=2026, month=1, total_spending=2000.00,
            by_category={"food": 500.00, "transport": 300.00},
        ))
        forecaster.add_historical_data(MonthlySpendingData(
            year=2026, month=2, total_spending=2200.00,
            by_category={"food": 600.00, "transport": 250.00},
        ))
        
        forecasts = forecaster.forecast_simple_average(months_ahead=1)
        assert len(forecasts) == 1
        assert forecasts[0].forecast_amount == pytest.approx(2100.0, 0.1)
        assert forecasts[0].confidence > 0
    
    def test_forecast_trend(self):
        """Test trend-based forecasting."""
        forecaster = BudgetForecaster(min_data_points=2)
        
        # Increasing spending trend
        forecaster.add_historical_data(MonthlySpendingData(
            year=2026, month=1, total_spending=2000.00,
            by_category={},
        ))
        forecaster.add_historical_data(MonthlySpendingData(
            year=2026, month=2, total_spending=2500.00,
            by_category={},
        ))
        forecaster.add_historical_data(MonthlySpendingData(
            year=2026, month=3, total_spending=3000.00,
            by_category={},
        ))
        
        forecasts = forecaster.forecast_trend(months_ahead=1)
        assert len(forecasts) == 1
        # Should predict higher than recent average due to uptrend
        assert forecasts[0].forecast_amount > 2000.00
    
    def test_forecast_seasonal(self):
        """Test seasonal forecasting."""
        forecaster = BudgetForecaster()
        
        # Add 12 months of data with seasonal pattern
        for month in range(1, 13):
            # Higher spending in December
            spending = 3000.00 if month == 12 else 2000.00
            forecaster.add_historical_data(MonthlySpendingData(
                year=2025, month=month, total_spending=spending,
                by_category={},
            ))
        
        forecasts = forecaster.forecast_seasonal(months_ahead=1)
        assert len(forecasts) == 1
        assert forecasts[0].method == ForecastMethod.SEASONAL
    
    def test_forecast_insufficient_data_raises(self):
        """Test that insufficient data raises error."""
        forecaster = BudgetForecaster(min_data_points=3)
        
        forecaster.add_historical_data(MonthlySpendingData(
            year=2026, month=1, total_spending=2000.00,
            by_category={},
        ))
        
        with pytest.raises(ValueError, match="Need at least"):
            forecaster.forecast_simple_average(months_ahead=1)
    
    def test_get_best_forecast(self):
        """Test getting best forecast."""
        forecaster = BudgetForecaster(min_data_points=2)
        
        for month in range(1, 4):
            forecaster.add_historical_data(MonthlySpendingData(
                year=2026, month=month, total_spending=2000.00 + (month * 100),
                by_category={},
            ))
        
        best = forecaster.get_best_forecast(months_ahead=1)
        assert best is not None
        assert 0.0 <= best.confidence <= 1.0


class TestFinancialForecast:
    """Tests for comprehensive financial forecasts."""
    
    def test_generate_financial_forecast(self):
        """Test generating complete financial forecast."""
        # Create spending history
        spending_history = []
        for month in range(1, 4):
            spending_history.append(MonthlySpendingData(
                year=2026,
                month=month,
                total_spending=2000.00,
                by_category={"food": 500.00, "transport": 300.00},
            ))
        
        # Create goals
        deadline = datetime.now(timezone.utc) + timedelta(days=365)
        created = datetime.now(timezone.utc)
        
        goals = [
            FinancialGoal(
                goal_id=str(uuid.uuid4()),
                name="Vacation Fund",
                goal_type=GoalType.VACATION,
                target_amount=5000.00,
                current_amount=0.00,
                deadline=deadline,
                created_at=created,
            )
        ]
        
        # Generate forecast
        forecast = generate_financial_forecast(
            spending_history=spending_history,
            income=5000.00,
            goals=goals,
            months_ahead=1,
        )
        
        assert forecast.spending_forecast is not None
        assert forecast.savings_forecast == pytest.approx(3000.00, 100)
        assert len(forecast.goals_progress) == 1
        assert forecast.forecast_date is not None
    
    def test_forecast_with_negative_savings(self):
        """Test forecast when spending exceeds income."""
        spending_history = []
        for month in range(1, 4):
            spending_history.append(MonthlySpendingData(
                year=2026,
                month=month,
                total_spending=6000.00,
                by_category={},
            ))
        
        forecast = generate_financial_forecast(
            spending_history=spending_history,
            income=5000.00,
            goals=[],
            months_ahead=1,
        )
        
        assert forecast.savings_forecast < 0
        # Should have recommendation about spending exceeding income
        assert any("exceeds" in rec.lower() for rec in forecast.recommendations)
    
    def test_forecast_with_goal_on_track(self):
        """Test forecast when goal is on track."""
        spending_history = []
        for month in range(1, 4):
            spending_history.append(MonthlySpendingData(
                year=2026,
                month=month,
                total_spending=1000.00,
                by_category={},
            ))
        
        deadline = datetime.now(timezone.utc) + timedelta(days=30)
        created = datetime.now(timezone.utc)
        
        goals = [
            FinancialGoal(
                goal_id="goal1",
                name="Savings Goal",
                goal_type=GoalType.SAVINGS,
                target_amount=1000.00,
                current_amount=0.00,
                deadline=deadline,
                created_at=created,
            )
        ]
        
        forecast = generate_financial_forecast(
            spending_history=spending_history,
            income=4000.00,
            goals=goals,
            months_ahead=1,
        )
        
        assert forecast.goals_progress["goal1"]["on_track"] is True


class TestForecasterEdgeCases:
    """Tests for edge cases in forecasting."""
    
    def test_forecast_flat_spending(self):
        """Test forecasting with flat spending pattern."""
        forecaster = BudgetForecaster(min_data_points=2)
        
        # All months have same spending
        for month in range(1, 4):
            forecaster.add_historical_data(MonthlySpendingData(
                year=2026, month=month, total_spending=2000.00,
                by_category={},
            ))
        
        # Trend forecast should handle flat line gracefully
        forecasts = forecaster.forecast_trend(months_ahead=1)
        assert len(forecasts) == 1
        assert forecasts[0].forecast_amount == pytest.approx(2000.00, 10)
    
    def test_forecast_multiple_months_ahead(self):
        """Test forecasting multiple months ahead."""
        forecaster = BudgetForecaster(min_data_points=2)
        
        for month in range(1, 4):
            forecaster.add_historical_data(MonthlySpendingData(
                year=2026, month=month, total_spending=2000.00,
                by_category={},
            ))
        
        forecasts = forecaster.forecast_simple_average(months_ahead=3)
        assert len(forecasts) == 3
        
        # Check that months are sequential
        assert forecasts[0].month == 4
        assert forecasts[1].month == 5
        assert forecasts[2].month == 6
    
    def test_forecast_year_boundary(self):
        """Test forecasting across year boundary."""
        forecaster = BudgetForecaster(min_data_points=2)
        
        # Add data for Nov, Dec
        forecaster.add_historical_data(MonthlySpendingData(
            year=2026, month=11, total_spending=2000.00,
            by_category={},
        ))
        forecaster.add_historical_data(MonthlySpendingData(
            year=2026, month=12, total_spending=2500.00,
            by_category={},
        ))
        
        forecasts = forecaster.forecast_simple_average(months_ahead=2)
        
        # First forecast should be Jan 2027
        assert forecasts[0].year == 2027
        assert forecasts[0].month == 1
        # Second forecast should be Feb 2027
        assert forecasts[1].year == 2027
        assert forecasts[1].month == 2
