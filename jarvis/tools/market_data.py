"""WTI Crude Oil and S&P 500 index live price fetchers."""

import httpx
from datetime import datetime, timezone
from typing import Optional

_OIL_CACHE: Optional[dict] = None
_OIL_CACHE_TS: float = 0.0
_OIL_CACHE_TTL_SEC = 20.0

_SP500_CACHE: Optional[dict] = None
_SP500_CACHE_TS: float = 0.0
_SP500_CACHE_TTL_SEC = 20.0

# --- OIL ---
def fetch_oil_price_live() -> dict:
    """
    Fetch live WTI Crude Oil price from public API (Yahoo Finance).
    Returns:
        {
            "price": float,
            "timestamp": str,
            "source": "yahoo_finance",
            "symbol": "CL=F",
            "currency": "USD"
        }
    """
    global _OIL_CACHE, _OIL_CACHE_TS
    now = datetime.now(timezone.utc)
    now_ts = now.timestamp()
    if _OIL_CACHE and (now_ts - _OIL_CACHE_TS) < _OIL_CACHE_TTL_SEC:
        return _OIL_CACHE
    try:
        # Yahoo Finance API (unofficial, public endpoint)
        url = "https://query1.finance.yahoo.com/v8/finance/chart/CL=F?interval=1m&range=1d"
        resp = httpx.get(url, timeout=2.8)
        resp.raise_for_status()
        data = resp.json()
        result = data["chart"]["result"][0]
        price = result["meta"]["regularMarketPrice"]
        out = {
            "price": float(price),
            "timestamp": now.isoformat(),
            "source": "yahoo_finance",
            "symbol": "CL=F",
            "currency": "USD"
        }
        _OIL_CACHE = out
        _OIL_CACHE_TS = now_ts
        return out
    except Exception as e:
        if _OIL_CACHE:
            return _OIL_CACHE
        raise RuntimeError(f"Oil price fetch failed: {e}")

def fetch_oil_price_dry_run(mock_price: float = 78.40) -> dict:
    return {
        "price": mock_price,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": "dry_run",
        "symbol": "CL=F",
        "currency": "USD"
    }

def get_oil_market_data(mode: str = "dry_run", mock_price: Optional[float] = None) -> dict:
    if mode == "dry_run":
        return fetch_oil_price_dry_run(mock_price or 78.40)
    elif mode == "live":
        return fetch_oil_price_live()
    else:
        raise ValueError(f"Unknown oil market mode: {mode}")

# --- S&P 500 ---
def fetch_sp500_price_live() -> dict:
    """
    Fetch live S&P 500 index price from Yahoo Finance.
    Returns:
        {
            "price": float,
            "timestamp": str,
            "source": "yahoo_finance",
            "symbol": "^GSPC",
            "currency": "USD"
        }
    """
    global _SP500_CACHE, _SP500_CACHE_TS
    now = datetime.now(timezone.utc)
    now_ts = now.timestamp()
    if _SP500_CACHE and (now_ts - _SP500_CACHE_TS) < _SP500_CACHE_TTL_SEC:
        return _SP500_CACHE
    try:
        url = "https://query1.finance.yahoo.com/v8/finance/chart/%5EGSPC?interval=1m&range=1d"
        resp = httpx.get(url, timeout=2.8)
        resp.raise_for_status()
        data = resp.json()
        result = data["chart"]["result"][0]
        price = result["meta"]["regularMarketPrice"]
        out = {
            "price": float(price),
            "timestamp": now.isoformat(),
            "source": "yahoo_finance",
            "symbol": "^GSPC",
            "currency": "USD"
        }
        _SP500_CACHE = out
        _SP500_CACHE_TS = now_ts
        return out
    except Exception as e:
        if _SP500_CACHE:
            return _SP500_CACHE
        raise RuntimeError(f"S&P 500 price fetch failed: {e}")

def fetch_sp500_price_dry_run(mock_price: float = 5100.00) -> dict:
    return {
        "price": mock_price,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": "dry_run",
        "symbol": "^GSPC",
        "currency": "USD"
    }

def get_sp500_market_data(mode: str = "dry_run", mock_price: Optional[float] = None) -> dict:
    if mode == "dry_run":
        return fetch_sp500_price_dry_run(mock_price or 5100.00)
    elif mode == "live":
        return fetch_sp500_price_live()
    else:
        raise ValueError(f"Unknown sp500 market mode: {mode}")
