"""Tests for XAUUSD market data module."""

import pytest
from unittest.mock import patch, MagicMock
from jarvis.tools.gold import (
    fetch_gold_price_dry_run,
    fetch_gold_price_live,
    get_gold_market_data
)


class TestGoldPriceDryRun:
    """Test dry-run gold price fetching."""
    
    def test_dry_run_returns_valid_structure(self):
        """Dry-run returns dict with required fields."""
        result = fetch_gold_price_dry_run()
        
        assert isinstance(result, dict)
        assert "price" in result
        assert "timestamp" in result
        assert "source" in result
        assert "currency" in result
        assert "metal" in result
        
    def test_dry_run_default_price(self):
        """Default dry-run price is realistic."""
        result = fetch_gold_price_dry_run()
        
        assert result["price"] == 2050.25
        assert result["currency"] == "USD"
        assert result["metal"] == "XAU"
        assert result["source"] == "dry_run"
        
    def test_dry_run_custom_price(self):
        """Custom price can be passed to dry-run."""
        result = fetch_gold_price_dry_run(mock_price=2100.00)
        
        assert result["price"] == 2100.00
        
    def test_dry_run_timestamp_is_iso(self):
        """Timestamp is valid ISO 8601."""
        result = fetch_gold_price_dry_run()
        
        # Should not raise if it's valid ISO 8601
        assert "T" in result["timestamp"]
        assert "+" in result["timestamp"] or "Z" in result["timestamp"]


class TestGoldPriceLive:
    """Test live gold price fetching."""
    
    @patch("jarvis.tools.gold.httpx.get")
    def test_live_fetch_success(self, mock_get):
        """Live fetch with valid API response."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"price": 2050.25}
        mock_get.return_value = mock_response
        
        result = fetch_gold_price_live()
        
        assert result["price"] == 2050.25
        assert result["source"] == "metals_api"
        assert result["currency"] == "USD"
        assert result["metal"] == "XAU"
        
    @patch("jarvis.tools.gold.httpx.get")
    def test_live_fetch_missing_price(self, mock_get):
        """Live fetch fails if response lacks price field."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"timestamp": "2026-04-27T00:00:00Z"}
        mock_get.return_value = mock_response
        
        with pytest.raises(RuntimeError, match="No price field"):
            fetch_gold_price_live()
            
    @patch("jarvis.tools.gold.httpx.get")
    def test_live_fetch_network_error(self, mock_get):
        """Live fetch raises RuntimeError on network failure."""
        mock_get.side_effect = Exception("Connection timeout")
        
        with pytest.raises(RuntimeError, match="Gold price fetch failed"):
            fetch_gold_price_live()


class TestGetGoldMarketData:
    """Test unified market data getter."""
    
    def test_get_dry_run_mode(self):
        """Unified getter supports dry_run mode."""
        result = get_gold_market_data(mode="dry_run")
        
        assert result["source"] == "dry_run"
        assert result["price"] == 2050.25
        
    def test_get_dry_run_with_custom_price(self):
        """Unified getter passes custom price to dry-run."""
        result = get_gold_market_data(mode="dry_run", mock_price=2000.00)
        
        assert result["price"] == 2000.00
        
    @patch("jarvis.tools.gold.httpx.get")
    def test_get_live_mode(self, mock_get):
        """Unified getter supports live mode."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"price": 2075.50}
        mock_get.return_value = mock_response
        
        result = get_gold_market_data(mode="live")
        
        assert result["source"] == "metals_api"
        assert result["price"] == 2075.50
        
    def test_get_invalid_mode(self):
        """Unified getter rejects unknown mode."""
        with pytest.raises(ValueError, match="Unknown gold market mode"):
            get_gold_market_data(mode="invalid")
            
    def test_get_default_is_dry_run(self):
        """Unified getter defaults to dry_run mode."""
        result = get_gold_market_data()
        
        assert result["source"] == "dry_run"
