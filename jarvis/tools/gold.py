"""XAUUSD market data and gold trading context."""

import httpx
from datetime import datetime, timezone
from typing import Optional


_GOLD_CACHE: Optional[dict] = None
_GOLD_CACHE_TS: float = 0.0
_GOLD_CACHE_TTL_SEC = 20.0


def _parse_live_gold_payload(payload: object) -> float:
    """Extract a gold spot price from known API response shapes."""
    if isinstance(payload, dict):
        price = payload.get("price") or payload.get("gold")
        if price is not None:
            return float(price)
    if isinstance(payload, list) and payload:
        first = payload[0]
        if isinstance(first, dict):
            if first.get("gold") is not None:
                return float(first["gold"])
            if first.get("price") is not None:
                return float(first["price"])
    raise RuntimeError("No parseable gold price in API response")


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
    global _GOLD_CACHE, _GOLD_CACHE_TS
    now = datetime.now(timezone.utc)
    now_ts = now.timestamp()

    if _GOLD_CACHE and (now_ts - _GOLD_CACHE_TS) < _GOLD_CACHE_TTL_SEC:
        return _GOLD_CACHE

    try:
        # Using metals-api (free tier available)
        # Alternative: use alphavantage or other commodity APIs
        response = httpx.get(
            "https://api.metals.live/v1/spot/gold",
            timeout=2.8
        )
        response.raise_for_status()
        data = response.json()

        price = _parse_live_gold_payload(data)

        result = {
            "price": float(price),
            "timestamp": now.isoformat(),
            "source": "metals_api",
            "currency": "USD",
            "metal": "XAU"
        }
        _GOLD_CACHE = result
        _GOLD_CACHE_TS = now_ts
        return result
    except Exception as e:
        if _GOLD_CACHE:
            return _GOLD_CACHE
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
