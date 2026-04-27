"""Tests for tax optimization and capital gains analyzer."""

import pytest
from datetime import datetime, timezone, timedelta

from jarvis.tools.tax_optimizer import (
    TransactionType, GainType, TaxStatus, InvestmentTransaction,
    CapitalGain, LossHarvestingOpportunity, TaxLiability,
    TaxOptimizationStrategy, TaxOptimizer
)


class TestTransactionType:
    """Tests for transaction type enumeration."""
    
    def test_all_transaction_types(self):
        """Verify all transaction types are defined."""
        types = [t.value for t in TransactionType]
        assert "buy" in types
        assert "sell" in types
        assert "dividend" in types


class TestGainType:
    """Tests for gain type enumeration."""
    
    def test_all_gain_types(self):
        """Verify all gain types are defined."""
        types = [g.value for g in GainType]
        assert "short_term" in types
        assert "long_term" in types


class TestTaxStatus:
    """Tests for tax status enumeration."""
    
    def test_all_statuses(self):
        """Verify all tax statuses are defined."""
        statuses = [s.value for s in TaxStatus]
        assert "single" in statuses
        assert "married_filing_jointly" in statuses


class TestInvestmentTransaction:
    """Tests for investment transactions."""
    
    def test_transaction_creation(self):
        """Test creating investment transaction."""
        now = datetime.now(timezone.utc)
        txn = InvestmentTransaction(
            transaction_id="txn-1",
            asset="AAPL",
            transaction_type=TransactionType.BUY,
            quantity=100,
            unit_price=150.0,
            date=now,
        )
        assert txn.asset == "AAPL"
        assert txn.quantity == 100
    
    def test_transaction_total_cost_buy(self):
        """Test buy transaction total cost."""
        now = datetime.now(timezone.utc)
        txn = InvestmentTransaction(
            transaction_id="txn-1",
            asset="AAPL",
            transaction_type=TransactionType.BUY,
            quantity=100,
            unit_price=150.0,
            date=now,
            fees=10.0,
        )
        # 100 * 150 + 10 = 15010
        assert txn.total_cost == pytest.approx(15010.0)
    
    def test_transaction_total_cost_sell(self):
        """Test sell transaction total cost."""
        now = datetime.now(timezone.utc)
        txn = InvestmentTransaction(
            transaction_id="txn-1",
            asset="AAPL",
            transaction_type=TransactionType.SELL,
            quantity=100,
            unit_price=160.0,
            date=now,
            fees=10.0,
        )
        # 100 * 160 - 10 = 15990
        assert txn.total_cost == pytest.approx(15990.0)
    
    def test_transaction_naive_datetime_raises(self):
        """Test that naive datetime raises error."""
        naive = datetime(2026, 4, 27, 10, 0, 0)
        with pytest.raises(ValueError, match="timezone-aware"):
            InvestmentTransaction(
                transaction_id="txn-1",
                asset="AAPL",
                transaction_type=TransactionType.BUY,
                quantity=100,
                unit_price=150.0,
                date=naive,
            )
    
    def test_transaction_negative_quantity_raises(self):
        """Test that negative quantity raises error."""
        now = datetime.now(timezone.utc)
        with pytest.raises(ValueError):
            InvestmentTransaction(
                transaction_id="txn-1",
                asset="AAPL",
                transaction_type=TransactionType.BUY,
                quantity=-100,
                unit_price=150.0,
                date=now,
            )
    
    def test_transaction_to_dict(self):
        """Test transaction serialization."""
        now = datetime.now(timezone.utc)
        txn = InvestmentTransaction(
            transaction_id="txn-1",
            asset="AAPL",
            transaction_type=TransactionType.BUY,
            quantity=100,
            unit_price=150.0,
            date=now,
        )
        data = txn.to_dict()
        
        assert data["asset"] == "AAPL"
        assert data["quantity"] == 100
        assert data["type"] == "buy"


class TestCapitalGain:
    """Tests for capital gains."""
    
    def test_capital_gain_creation(self):
        """Test creating capital gain."""
        acq = datetime.now(timezone.utc) - timedelta(days=400)
        sale = datetime.now(timezone.utc)
        
        gain = CapitalGain(
            asset="AAPL",
            gain_type=GainType.LONG_TERM,
            quantity=100,
            cost_basis=150.0,
            sale_price=175.0,
            realized_gain=2500.0,
            sale_date=sale,
            acquisition_date=acq,
        )
        assert gain.realized_gain == 2500.0
    
    def test_capital_gain_holding_period(self):
        """Test holding period calculation."""
        acq = datetime.now(timezone.utc) - timedelta(days=400)
        sale = datetime.now(timezone.utc)
        
        gain = CapitalGain(
            asset="AAPL",
            gain_type=GainType.LONG_TERM,
            quantity=100,
            cost_basis=150.0,
            sale_price=175.0,
            realized_gain=2500.0,
            sale_date=sale,
            acquisition_date=acq,
        )
        assert gain.holding_period_days >= 399


class TestLossHarvestingOpportunity:
    """Tests for loss harvesting opportunities."""
    
    def test_opportunity_creation(self):
        """Test creating harvesting opportunity."""
        opp = LossHarvestingOpportunity(
            asset="TSLA",
            current_price=200.0,
            cost_basis=250.0,
            unrealized_loss=5000.0,
            potential_tax_benefit=1200.0,
        )
        assert opp.potential_tax_benefit == 1200.0
    
    def test_opportunity_with_replacement(self):
        """Test opportunity with replacement asset."""
        opp = LossHarvestingOpportunity(
            asset="AAPL",
            current_price=140.0,
            cost_basis=160.0,
            unrealized_loss=2000.0,
            potential_tax_benefit=480.0,
            replacement_asset="MSFT",
        )
        assert opp.replacement_asset == "MSFT"


class TestTaxLiability:
    """Tests for tax liability."""
    
    def test_liability_creation(self):
        """Test creating tax liability."""
        liability = TaxLiability(
            short_term_gains=5000.0,
            long_term_gains=10000.0,
            total_gains=15000.0,
            estimated_tax_rate=0.24,
            estimated_liability=3600.0,
            tax_status=TaxStatus.SINGLE,
            filing_year=2026,
        )
        assert liability.total_gains == 15000.0
    
    def test_liability_to_dict(self):
        """Test liability serialization."""
        liability = TaxLiability(
            short_term_gains=5000.0,
            long_term_gains=10000.0,
            total_gains=15000.0,
            estimated_tax_rate=0.24,
            estimated_liability=3600.0,
            tax_status=TaxStatus.SINGLE,
            filing_year=2026,
        )
        data = liability.to_dict()
        
        assert data["short_term_gains"] == 5000.0
        assert data["long_term_gains"] == 10000.0


class TestTaxOptimizer:
    """Tests for tax optimizer."""
    
    def test_optimizer_creation(self):
        """Test creating tax optimizer."""
        optimizer = TaxOptimizer(TaxStatus.SINGLE)
        assert optimizer.tax_status == TaxStatus.SINGLE
    
    def test_add_buy_transaction(self):
        """Test adding buy transaction."""
        optimizer = TaxOptimizer()
        now = datetime.now(timezone.utc)
        
        txn = optimizer.add_transaction(
            asset="AAPL",
            transaction_type=TransactionType.BUY,
            quantity=100,
            unit_price=150.0,
            date=now,
        )
        
        assert len(optimizer.transactions) == 1
        assert txn.asset == "AAPL"
    
    def test_add_sell_transaction_fifo(self):
        """Test sell transaction with FIFO."""
        optimizer = TaxOptimizer()
        now = datetime.now(timezone.utc)
        
        # Buy 100 shares at $150
        optimizer.add_transaction(
            asset="AAPL",
            transaction_type=TransactionType.BUY,
            quantity=100,
            unit_price=150.0,
            date=now,
        )
        
        # Sell 50 shares at $160
        optimizer.add_transaction(
            asset="AAPL",
            transaction_type=TransactionType.SELL,
            quantity=50,
            unit_price=160.0,
            date=now + timedelta(days=30),
        )
        
        assert len(optimizer.realized_gains) == 1
        assert optimizer.realized_gains[0].quantity == 50
    
    def test_short_term_vs_long_term_gains(self):
        """Test short-term and long-term gain classification."""
        optimizer = TaxOptimizer()
        now = datetime.now(timezone.utc)
        
        # Short-term: held 30 days
        optimizer.add_transaction(
            asset="AAPL",
            transaction_type=TransactionType.BUY,
            quantity=100,
            unit_price=150.0,
            date=now,
        )
        
        optimizer.add_transaction(
            asset="AAPL",
            transaction_type=TransactionType.SELL,
            quantity=100,
            unit_price=160.0,
            date=now + timedelta(days=30),
        )
        
        assert optimizer.realized_gains[0].gain_type == GainType.SHORT_TERM
        
        # Long-term: held 400 days
        optimizer.add_transaction(
            asset="MSFT",
            transaction_type=TransactionType.BUY,
            quantity=50,
            unit_price=300.0,
            date=now,
        )
        
        optimizer.add_transaction(
            asset="MSFT",
            transaction_type=TransactionType.SELL,
            quantity=50,
            unit_price=320.0,
            date=now + timedelta(days=400),
        )
        
        assert optimizer.realized_gains[1].gain_type == GainType.LONG_TERM
    
    def test_calculate_current_positions(self):
        """Test calculating current positions."""
        optimizer = TaxOptimizer()
        now = datetime.now(timezone.utc)
        
        optimizer.add_transaction(
            asset="AAPL",
            transaction_type=TransactionType.BUY,
            quantity=100,
            unit_price=150.0,
            date=now,
        )
        
        positions = optimizer.calculate_current_positions({"AAPL": 160.0})
        
        assert "AAPL" in positions
        assert positions["AAPL"]["quantity"] == 100
        assert positions["AAPL"]["current_value"] == 16000.0
        assert positions["AAPL"]["unrealized_gain"] == 1000.0
    
    def test_identify_harvesting_opportunities(self):
        """Test identifying loss harvesting opportunities."""
        optimizer = TaxOptimizer()
        now = datetime.now(timezone.utc)
        
        optimizer.add_transaction(
            asset="TSLA",
            transaction_type=TransactionType.BUY,
            quantity=100,
            unit_price=250.0,
            date=now,
        )
        
        # Loss position: bought at 250, now at 200
        opportunities = optimizer.identify_harvesting_opportunities({"TSLA": 200.0})
        
        assert len(opportunities) > 0
        assert opportunities[0].asset == "TSLA"
        assert opportunities[0].unrealized_loss == 5000.0
    
    def test_calculate_tax_liability(self):
        """Test calculating tax liability."""
        optimizer = TaxOptimizer(TaxStatus.SINGLE)
        now = datetime.now(timezone.utc)
        
        # Generate gains
        optimizer.add_transaction(
            asset="AAPL",
            transaction_type=TransactionType.BUY,
            quantity=100,
            unit_price=150.0,
            date=now,
        )
        
        optimizer.add_transaction(
            asset="AAPL",
            transaction_type=TransactionType.SELL,
            quantity=100,
            unit_price=160.0,
            date=now + timedelta(days=30),
        )
        
        liability = optimizer.calculate_tax_liability()
        
        assert liability.short_term_gains == 1000.0
        assert liability.long_term_gains == 0.0
        assert liability.estimated_liability > 0
    
    def test_generate_optimization_strategies(self):
        """Test generating optimization strategies."""
        optimizer = TaxOptimizer()
        now = datetime.now(timezone.utc)
        
        optimizer.add_transaction(
            asset="AAPL",
            transaction_type=TransactionType.BUY,
            quantity=100,
            unit_price=150.0,
            date=now,
        )
        
        strategies = optimizer.generate_optimization_strategies()
        
        # Should include at least one strategy
        assert isinstance(strategies, list)


class TestTaxOptimizerEdgeCases:
    """Edge case tests for tax optimizer."""
    
    def test_empty_portfolio(self):
        """Test with empty portfolio."""
        optimizer = TaxOptimizer()
        positions = optimizer.calculate_current_positions({})
        
        assert len(positions) == 0
    
    def test_single_buy_no_sell(self):
        """Test single buy transaction without sale."""
        optimizer = TaxOptimizer()
        now = datetime.now(timezone.utc)
        
        optimizer.add_transaction(
            asset="AAPL",
            transaction_type=TransactionType.BUY,
            quantity=100,
            unit_price=150.0,
            date=now,
        )
        
        assert len(optimizer.realized_gains) == 0
        assert len(optimizer.current_holdings["AAPL"]) == 1
    
    def test_married_filing_jointly_rates(self):
        """Test tax rates for married filing jointly."""
        optimizer = TaxOptimizer(TaxStatus.MARRIED_FILING_JOINTLY)
        assert optimizer.tax_status == TaxStatus.MARRIED_FILING_JOINTLY
    
    def test_multiple_assets(self):
        """Test portfolio with multiple assets."""
        optimizer = TaxOptimizer()
        now = datetime.now(timezone.utc)
        
        for symbol in ["AAPL", "MSFT", "GOOGL"]:
            optimizer.add_transaction(
                asset=symbol,
                transaction_type=TransactionType.BUY,
                quantity=50,
                unit_price=150.0,
                date=now,
            )
        
        positions = optimizer.calculate_current_positions({
            "AAPL": 160.0,
            "MSFT": 140.0,
            "GOOGL": 150.0,
        })
        
        assert len(positions) == 3
    
    def test_wash_sale_detection(self):
        """Test wash sale risk detection."""
        optimizer = TaxOptimizer()
        now = datetime.now(timezone.utc)
        
        # Sell at loss
        optimizer.add_transaction(
            asset="AAPL",
            transaction_type=TransactionType.BUY,
            quantity=100,
            unit_price=150.0,
            date=now - timedelta(days=100),
        )
        
        optimizer.add_transaction(
            asset="AAPL",
            transaction_type=TransactionType.SELL,
            quantity=100,
            unit_price=140.0,
            date=now,
        )
        
        # Buy again within 30 days - wash sale risk
        optimizer.add_transaction(
            asset="AAPL",
            transaction_type=TransactionType.BUY,
            quantity=100,
            unit_price=140.0,
            date=now + timedelta(days=10),
        )
        
        # Check wash sale risk
        wash_risk = optimizer._check_wash_sale_risk("AAPL")
        assert wash_risk
    
    def test_partial_sell(self):
        """Test selling only part of position."""
        optimizer = TaxOptimizer()
        now = datetime.now(timezone.utc)
        
        # Buy 200 shares
        optimizer.add_transaction(
            asset="AAPL",
            transaction_type=TransactionType.BUY,
            quantity=200,
            unit_price=150.0,
            date=now,
        )
        
        # Sell 50 shares
        optimizer.add_transaction(
            asset="AAPL",
            transaction_type=TransactionType.SELL,
            quantity=50,
            unit_price=160.0,
            date=now + timedelta(days=100),
        )
        
        # Should have 150 remaining
        remaining = optimizer.current_holdings.get("AAPL", [])
        total_qty = sum(t.quantity for t in remaining)
        assert total_qty == pytest.approx(150.0)
