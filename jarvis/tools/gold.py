"""XAUUSD market data and gold trading context."""

import httpx
import json
from datetime import datetime, timezone
from typing import Optional


def fetch_gold_price_live() -> dict:
    """
    Fetch live XAU/USD (gold) spot price from public API.
    
    Returns:
        {
            "price": float,  # current XAU/USD spot price (USD per troy ounce)
            "timestamp": str,  # ISO 8601 timestamp
            "source": "metals_api",
            "currency": "USD",
            "metal": "XAU"
        }
        
    Raises:
        RuntimeError: if API call fails
    """
    try:
        # Using metals-api (free tier available)
        # Alternative: use alphavantage or other commodity APIs
        response = httpx.get(
            "https://api.metals.live/v1/spot/gold",
            timeout=5.0
        )
        response.raise_for_status()
        data = response.json()
        
        # metals.live returns: {"price": 2050.25, ...}
        price = data.get("price")
        if price is None:
            raise RuntimeError("No price field in API response")
        
        return {
            "price": float(price),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": "metals_api",
            "currency": "USD",
            "metal": "XAU"
        }
    except Exception as e:
        raise RuntimeError(f"Gold price fetch failed: {e}")


def fetch_gold_price_dry_run(mock_price: float = 2050.25) -> dict:
    """
    Return deterministic mock gold price for testing/dry-run.
    
    Args:
        mock_price: Price to return (default realistic XAU/USD)
        
    Returns:
        Mock price response with same schema as live fetch
    """
    return {
        "price": mock_price,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": "dry_run",
        "currency": "USD",
        "metal": "XAU"
    }


def get_gold_market_data(mode: str = "dry_run", mock_price: Optional[float] = None) -> dict:
    """
    Unified market data getter supporting dry_run and live modes.
    
    Args:
        mode: "dry_run" or "live"
        mock_price: Override mock price (only used in dry_run mode)
        
    Returns:
        Market data dict with price, timestamp, source, currency, metal
        
    Raises:
        RuntimeError: if live mode requested but API fetch fails
    """
    if mode == "dry_run":
        return fetch_gold_price_dry_run(mock_price or 2050.25)
    elif mode == "live":
        return fetch_gold_price_live()
    else:
        raise ValueError(f"Unknown gold market mode: {mode}")
