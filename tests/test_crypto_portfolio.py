"""Tests for cryptocurrency portfolio tracker module."""

import pytest
from datetime import datetime, timezone, timedelta
from pathlib import Path
import tempfile
import json

from jarvis.tools.crypto_portfolio import (
    CryptoAsset, PriceQuote, Holding, Portfolio, Trade,
    PortfolioManager, get_portfolio_summary
)


class TestCryptoAsset:
    """Tests for cryptocurrency asset enumeration."""
    
    def test_all_assets_defined(self):
        """Verify major crypto assets are defined."""
        assets = [asset.value for asset in CryptoAsset]
        assert "btc" in assets
        assert "eth" in assets
        assert "sol" in assets
        assert "usdc" in assets


class TestPriceQuote:
    """Tests for price quote creation and validation."""
    
    def test_price_quote_creation(self):
        """Test creating a valid price quote."""
        ts = datetime(2026, 4, 27, 10, 30, 0, tzinfo=timezone.utc)
        quote = PriceQuote(
            asset=CryptoAsset.BTC,
            price_usd=45000.00,
            timestamp=ts,
            source="coingecko",
        )
        assert quote.price_usd == 45000.00
        assert quote.asset == CryptoAsset.BTC
        assert quote.source == "coingecko"
    
    def test_price_quote_with_market_data(self):
        """Test price quote with market cap and volume."""
        ts = datetime.now(timezone.utc)
        quote = PriceQuote(
            asset=CryptoAsset.ETH,
            price_usd=2500.00,
            timestamp=ts,
            market_cap_usd=300000000000.0,
            volume_24h_usd=20000000000.0,
            change_24h_percent=5.5,
        )
        assert quote.market_cap_usd is not None
        assert quote.change_24h_percent == 5.5
    
    def test_price_quote_with_zero_price_raises(self):
        """Test that zero price raises validation error."""
        ts = datetime.now(timezone.utc)
        with pytest.raises(ValueError, match="Price must be positive"):
            PriceQuote(
                asset=CryptoAsset.BTC,
                price_usd=0.0,
                timestamp=ts,
            )
    
    def test_price_quote_with_naive_datetime_raises(self):
        """Test that naive datetime raises error."""
        ts = datetime(2026, 4, 27, 10, 30, 0)  # No timezone
        with pytest.raises(ValueError, match="timezone-aware"):
            PriceQuote(
                asset=CryptoAsset.BTC,
                price_usd=45000.0,
                timestamp=ts,
            )


class TestHolding:
    """Tests for cryptocurrency holdings."""
    
    def test_holding_creation(self):
        """Test creating a valid holding."""
        ts = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        holding = Holding(
            asset=CryptoAsset.BTC,
            quantity=2.5,
            average_cost_usd=30000.0,
            purchased_at=ts,
        )
        assert holding.quantity == 2.5
        assert holding.average_cost_usd == 30000.0
    
    def test_cost_basis_calculation(self):
        """Test cost basis calculation."""
        ts = datetime.now(timezone.utc)
        holding = Holding(
            asset=CryptoAsset.ETH,
            quantity=10.0,
            average_cost_usd=2000.0,
            purchased_at=ts,
        )
        assert holding.cost_basis() == 20000.0
    
    def test_current_value_calculation(self):
        """Test current value calculation."""
        ts = datetime.now(timezone.utc)
        holding = Holding(
            asset=CryptoAsset.BTC,
            quantity=1.0,
            average_cost_usd=40000.0,
            purchased_at=ts,
        )
        current_value = holding.current_value(50000.0)
        assert current_value == 50000.0
    
    def test_unrealized_pnl_positive(self):
        """Test unrealized P&L calculation (gain)."""
        ts = datetime.now(timezone.utc)
        holding = Holding(
            asset=CryptoAsset.BTC,
            quantity=1.0,
            average_cost_usd=40000.0,
            purchased_at=ts,
        )
        pnl = holding.unrealized_pnl(50000.0)
        assert pnl == 10000.0
    
    def test_unrealized_pnl_negative(self):
        """Test unrealized P&L calculation (loss)."""
        ts = datetime.now(timezone.utc)
        holding = Holding(
            asset=CryptoAsset.BTC,
            quantity=1.0,
            average_cost_usd=40000.0,
            purchased_at=ts,
        )
        pnl = holding.unrealized_pnl(35000.0)
        assert pnl == -5000.0
    
    def test_pnl_percentage(self):
        """Test P&L percentage calculation."""
        ts = datetime.now(timezone.utc)
        holding = Holding(
            asset=CryptoAsset.BTC,
            quantity=1.0,
            average_cost_usd=40000.0,
            purchased_at=ts,
        )
        pnl_pct = holding.pnl_percentage(50000.0)
        assert pnl_pct == 25.0  # 10000 / 40000 * 100


class TestPortfolio:
    """Tests for cryptocurrency portfolio management."""
    
    def test_portfolio_creation(self):
        """Test creating a portfolio."""
        ts = datetime.now(timezone.utc)
        portfolio = Portfolio(
            portfolio_id="port1",
            owner_name="Alice",
            created_at=ts,
        )
        assert portfolio.owner_name == "Alice"
        assert len(portfolio.holdings) == 0
    
    def test_add_holding(self):
        """Test adding a holding to portfolio."""
        ts = datetime.now(timezone.utc)
        portfolio = Portfolio(
            portfolio_id="port1",
            owner_name="Alice",
            created_at=ts,
        )
        
        holding = Holding(
            asset=CryptoAsset.BTC,
            quantity=1.0,
            average_cost_usd=40000.0,
            purchased_at=ts,
        )
        portfolio.add_holding(holding)
        
        assert len(portfolio.holdings) == 1
        assert portfolio.holdings["btc"] is not None
    
    def test_update_price(self):
        """Test updating price quotes."""
        ts = datetime.now(timezone.utc)
        portfolio = Portfolio(
            portfolio_id="port1",
            owner_name="Alice",
            created_at=ts,
        )
        
        quote = PriceQuote(
            asset=CryptoAsset.BTC,
            price_usd=45000.0,
            timestamp=ts,
        )
        portfolio.update_price(quote)
        
        assert len(portfolio.price_history["btc"]) == 1
    
    def test_get_latest_price(self):
        """Test getting the latest price."""
        ts1 = datetime(2026, 4, 27, 10, 0, 0, tzinfo=timezone.utc)
        ts2 = datetime(2026, 4, 27, 11, 0, 0, tzinfo=timezone.utc)
        
        portfolio = Portfolio(
            portfolio_id="port1",
            owner_name="Alice",
            created_at=ts1,
        )
        
        portfolio.update_price(PriceQuote(
            asset=CryptoAsset.BTC,
            price_usd=45000.0,
            timestamp=ts1,
        ))
        portfolio.update_price(PriceQuote(
            asset=CryptoAsset.BTC,
            price_usd=46000.0,
            timestamp=ts2,
        ))
        
        latest = portfolio.get_latest_price(CryptoAsset.BTC)
        assert latest == 46000.0
    
    def test_total_cost_basis(self):
        """Test calculating total cost basis."""
        ts = datetime.now(timezone.utc)
        portfolio = Portfolio(
            portfolio_id="port1",
            owner_name="Alice",
            created_at=ts,
        )
        
        portfolio.add_holding(Holding(
            asset=CryptoAsset.BTC,
            quantity=1.0,
            average_cost_usd=40000.0,
            purchased_at=ts,
        ))
        portfolio.add_holding(Holding(
            asset=CryptoAsset.ETH,
            quantity=10.0,
            average_cost_usd=2000.0,
            purchased_at=ts,
        ))
        
        total_basis = portfolio.total_cost_basis()
        assert total_basis == 60000.0  # 40000 + 20000
    
    def test_total_current_value(self):
        """Test calculating total current value."""
        ts = datetime.now(timezone.utc)
        portfolio = Portfolio(
            portfolio_id="port1",
            owner_name="Alice",
            created_at=ts,
        )
        
        portfolio.add_holding(Holding(
            asset=CryptoAsset.BTC,
            quantity=1.0,
            average_cost_usd=40000.0,
            purchased_at=ts,
        ))
        
        portfolio.update_price(PriceQuote(
            asset=CryptoAsset.BTC,
            price_usd=50000.0,
            timestamp=ts,
        ))
        
        total_value = portfolio.total_current_value()
        assert total_value == 50000.0
    
    def test_unrealized_pnl(self):
        """Test unrealized P&L calculation."""
        ts = datetime.now(timezone.utc)
        portfolio = Portfolio(
            portfolio_id="port1",
            owner_name="Alice",
            created_at=ts,
        )
        
        portfolio.add_holding(Holding(
            asset=CryptoAsset.BTC,
            quantity=1.0,
            average_cost_usd=40000.0,
            purchased_at=ts,
        ))
        
        portfolio.update_price(PriceQuote(
            asset=CryptoAsset.BTC,
            price_usd=50000.0,
            timestamp=ts,
        ))
        
        pnl = portfolio.unrealized_pnl()
        assert pnl == 10000.0
    
    def test_allocation(self):
        """Test portfolio allocation calculation."""
        ts = datetime.now(timezone.utc)
        portfolio = Portfolio(
            portfolio_id="port1",
            owner_name="Alice",
            created_at=ts,
        )
        
        portfolio.add_holding(Holding(
            asset=CryptoAsset.BTC,
            quantity=1.0,
            average_cost_usd=40000.0,
            purchased_at=ts,
        ))
        portfolio.add_holding(Holding(
            asset=CryptoAsset.ETH,
            quantity=10.0,
            average_cost_usd=2000.0,
            purchased_at=ts,
        ))
        
        portfolio.update_price(PriceQuote(
            asset=CryptoAsset.BTC,
            price_usd=40000.0,
            timestamp=ts,
        ))
        portfolio.update_price(PriceQuote(
            asset=CryptoAsset.ETH,
            price_usd=2000.0,
            timestamp=ts,
        ))
        
        allocation = portfolio.allocation()
        assert allocation["btc"] == pytest.approx(66.67, 0.1)
        assert allocation["eth"] == pytest.approx(33.33, 0.1)
    
    def test_rebalancing_recommendation(self):
        """Test rebalancing recommendations."""
        ts = datetime.now(timezone.utc)
        portfolio = Portfolio(
            portfolio_id="port1",
            owner_name="Alice",
            created_at=ts,
            rebalance_target={"btc": 50.0, "eth": 50.0},
        )
        
        portfolio.add_holding(Holding(
            asset=CryptoAsset.BTC,
            quantity=1.0,
            average_cost_usd=40000.0,
            purchased_at=ts,
        ))
        portfolio.add_holding(Holding(
            asset=CryptoAsset.ETH,
            quantity=10.0,
            average_cost_usd=2000.0,
            purchased_at=ts,
        ))
        
        portfolio.update_price(PriceQuote(
            asset=CryptoAsset.BTC,
            price_usd=40000.0,
            timestamp=ts,
        ))
        portfolio.update_price(PriceQuote(
            asset=CryptoAsset.ETH,
            price_usd=2000.0,
            timestamp=ts,
        ))
        
        recommendations = portfolio.rebalancing_recommendation()
        # BTC is 66.67%, target is 50%, so should recommend selling
        if "btc" in recommendations:
            assert recommendations["btc"]["action"] == "sell"


class TestTrade:
    """Tests for cryptocurrency trades."""
    
    def test_trade_creation(self):
        """Test creating a trade."""
        ts = datetime.now(timezone.utc)
        trade = Trade(
            portfolio_id="port1",
            asset=CryptoAsset.BTC,
            action="buy",
            quantity=0.5,
            price_usd=45000.0,
            timestamp=ts,
        )
        assert trade.action == "buy"
        assert trade.quantity == 0.5
    
    def test_trade_total_usd(self):
        """Test calculating total USD value of trade."""
        ts = datetime.now(timezone.utc)
        trade = Trade(
            portfolio_id="port1",
            asset=CryptoAsset.ETH,
            action="buy",
            quantity=5.0,
            price_usd=2500.0,
            timestamp=ts,
        )
        assert trade.total_usd() == 12500.0
    
    def test_invalid_trade_action_raises(self):
        """Test that invalid action raises error."""
        ts = datetime.now(timezone.utc)
        with pytest.raises(ValueError, match="'buy' or 'sell'"):
            Trade(
                portfolio_id="port1",
                asset=CryptoAsset.BTC,
                action="hold",
                quantity=1.0,
                price_usd=45000.0,
                timestamp=ts,
            )


class TestPortfolioManager:
    """Tests for portfolio persistence and retrieval."""
    
    def test_manager_creation(self):
        """Test creating a portfolio manager."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = PortfolioManager(Path(tmpdir))
            assert manager.data_dir == Path(tmpdir)
    
    def test_create_portfolio(self):
        """Test creating a portfolio."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = PortfolioManager(Path(tmpdir))
            portfolio = manager.create_portfolio("Alice")
            
            assert portfolio.portfolio_id is not None
            assert portfolio.owner_name == "Alice"
            assert portfolio in manager.list_portfolios()
    
    def test_save_and_load_portfolio(self):
        """Test portfolio persistence."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = PortfolioManager(Path(tmpdir))
            
            # Create and populate portfolio
            portfolio = manager.create_portfolio("Alice")
            ts = datetime.now(timezone.utc)
            
            holding = Holding(
                asset=CryptoAsset.BTC,
                quantity=1.0,
                average_cost_usd=40000.0,
                purchased_at=ts,
            )
            portfolio.add_holding(holding)
            
            portfolio.update_price(PriceQuote(
                asset=CryptoAsset.BTC,
                price_usd=50000.0,
                timestamp=ts,
            ))
            
            # Save
            manager.save_portfolio(portfolio)
            
            # Load
            loaded = manager.load_portfolio(portfolio.portfolio_id)
            
            assert loaded is not None
            assert loaded.owner_name == "Alice"
            assert len(loaded.holdings) == 1
            assert loaded.get_latest_price(CryptoAsset.BTC) == 50000.0
    
    def test_load_nonexistent_portfolio(self):
        """Test loading nonexistent portfolio."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = PortfolioManager(Path(tmpdir))
            loaded = manager.load_portfolio("nonexistent")
            assert loaded is None


class TestPortfolioSummary:
    """Tests for portfolio summary generation."""
    
    def test_portfolio_summary(self):
        """Test generating portfolio summary."""
        ts = datetime.now(timezone.utc)
        portfolio = Portfolio(
            portfolio_id="port1",
            owner_name="Alice",
            created_at=ts,
        )
        
        portfolio.add_holding(Holding(
            asset=CryptoAsset.BTC,
            quantity=1.0,
            average_cost_usd=40000.0,
            purchased_at=ts,
        ))
        
        portfolio.update_price(PriceQuote(
            asset=CryptoAsset.BTC,
            price_usd=50000.0,
            timestamp=ts,
        ))
        
        summary = get_portfolio_summary(portfolio)
        assert summary["owner"] == "Alice"
        assert summary["holding_count"] == 1
        assert summary["total_cost_basis"] == 40000.0
        assert summary["total_current_value"] == 50000.0
        assert summary["unrealized_pnl"] == 10000.0
