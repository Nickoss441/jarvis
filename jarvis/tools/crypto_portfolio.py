"""Cryptocurrency portfolio tracker module.

Provides cryptocurrency holdings management, price tracking, P&L calculation,
portfolio rebalancing analysis, and integration with sentiment analysis for
trading signals.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from enum import Enum
from pathlib import Path
from typing import Optional
import json
import uuid


class CryptoAsset(str, Enum):
    """Cryptocurrency asset enumeration."""
    BTC = "btc"
    ETH = "eth"
    BNB = "bnb"
    XRP = "xrp"
    SOL = "sol"
    ADA = "ada"
    DOGE = "doge"
    MATIC = "matic"
    LINK = "link"
    USDT = "usdt"
    USDC = "usdc"
    DAI = "dai"
    OTHER = "other"


@dataclass
class PriceQuote:
    """Price quote for a cryptocurrency at a specific point in time.
    
    Attributes:
        asset: Cryptocurrency asset symbol
        price_usd: Price in USD
        timestamp: When this price was recorded (UTC)
        source: Data source (e.g., "coingecko", "binance", "kraken")
        market_cap_usd: Optional market capitalization
        volume_24h_usd: Optional 24-hour trading volume
        change_24h_percent: Optional 24-hour price change percentage
    """
    asset: CryptoAsset
    price_usd: float
    timestamp: datetime
    source: str = "manual"
    market_cap_usd: Optional[float] = None
    volume_24h_usd: Optional[float] = None
    change_24h_percent: Optional[float] = None
    
    def __post_init__(self):
        """Validate price quote data."""
        if self.price_usd <= 0:
            raise ValueError(f"Price must be positive, got {self.price_usd}")
        if not isinstance(self.timestamp, datetime):
            raise ValueError("timestamp must be a datetime object")
        if self.timestamp.tzinfo is None:
            raise ValueError("timestamp must be timezone-aware (UTC)")
    
    def to_dict(self) -> dict:
        """Convert price quote to dictionary."""
        return {
            "asset": self.asset.value,
            "price_usd": self.price_usd,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
            "market_cap_usd": self.market_cap_usd,
            "volume_24h_usd": self.volume_24h_usd,
            "change_24h_percent": self.change_24h_percent,
        }


@dataclass
class Holding:
    """A cryptocurrency holding in the portfolio.
    
    Attributes:
        asset: Cryptocurrency asset
        quantity: Amount held
        average_cost_usd: Average purchase price per unit
        purchased_at: When the holding was acquired
        metadata: Custom metadata (exchange, wallet address, etc.)
    """
    asset: CryptoAsset
    quantity: float
    average_cost_usd: float
    purchased_at: datetime
    metadata: dict = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate holding data."""
        if self.quantity <= 0:
            raise ValueError(f"Quantity must be positive, got {self.quantity}")
        if self.average_cost_usd < 0:
            raise ValueError(f"Average cost must be non-negative, got {self.average_cost_usd}")
        if not isinstance(self.purchased_at, datetime):
            raise ValueError("purchased_at must be a datetime object")
        if self.purchased_at.tzinfo is None:
            raise ValueError("purchased_at must be timezone-aware (UTC)")
    
    def cost_basis(self) -> float:
        """Calculate total cost basis for this holding."""
        return self.quantity * self.average_cost_usd
    
    def current_value(self, current_price: float) -> float:
        """Calculate current value at given price."""
        return self.quantity * current_price
    
    def unrealized_pnl(self, current_price: float) -> float:
        """Calculate unrealized profit/loss."""
        return self.current_value(current_price) - self.cost_basis()
    
    def pnl_percentage(self, current_price: float) -> float:
        """Calculate unrealized P&L as percentage."""
        basis = self.cost_basis()
        if basis == 0:
            return 0.0
        return (self.unrealized_pnl(current_price) / basis) * 100
    
    def to_dict(self) -> dict:
        """Convert holding to dictionary."""
        return {
            "asset": self.asset.value,
            "quantity": self.quantity,
            "average_cost_usd": self.average_cost_usd,
            "cost_basis": self.cost_basis(),
            "purchased_at": self.purchased_at.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class Portfolio:
    """Cryptocurrency portfolio with multiple holdings.
    
    Attributes:
        portfolio_id: Unique portfolio identifier
        owner_name: Portfolio owner name
        created_at: Portfolio creation timestamp (UTC)
        holdings: Dict of asset -> Holding
        price_history: Dict of asset -> list of PriceQuote
        rebalance_target: Optional target allocation percentages
    """
    portfolio_id: str
    owner_name: str
    created_at: datetime
    holdings: dict[str, Holding] = field(default_factory=dict)
    price_history: dict[str, list[PriceQuote]] = field(default_factory=dict)
    rebalance_target: dict[str, float] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate portfolio data."""
        if not isinstance(self.created_at, datetime):
            raise ValueError("created_at must be a datetime object")
        if self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware (UTC)")
    
    def add_holding(self, holding: Holding) -> None:
        """Add a holding to the portfolio."""
        asset_key = holding.asset.value
        if asset_key in self.holdings:
            raise ValueError(f"Holding for {asset_key} already exists")
        self.holdings[asset_key] = holding
        
        # Initialize price history for this asset
        if asset_key not in self.price_history:
            self.price_history[asset_key] = []
    
    def update_price(self, quote: PriceQuote) -> None:
        """Update price quote for an asset."""
        asset_key = quote.asset.value
        
        if asset_key not in self.price_history:
            self.price_history[asset_key] = []
        
        self.price_history[asset_key].append(quote)
    
    def get_latest_price(self, asset: CryptoAsset) -> Optional[float]:
        """Get the latest price for an asset."""
        asset_key = asset.value
        if asset_key not in self.price_history or not self.price_history[asset_key]:
            return None
        
        return self.price_history[asset_key][-1].price_usd
    
    def total_cost_basis(self) -> float:
        """Calculate total cost basis across all holdings."""
        return sum(holding.cost_basis() for holding in self.holdings.values())
    
    def total_current_value(self) -> float:
        """Calculate total current value across all holdings."""
        total = 0.0
        for asset_key, holding in self.holdings.items():
            price = self.get_latest_price(holding.asset)
            if price:
                total += holding.current_value(price)
            else:
                # Use cost basis if no price available
                total += holding.cost_basis()
        return total
    
    def unrealized_pnl(self) -> float:
        """Calculate total unrealized profit/loss."""
        return self.total_current_value() - self.total_cost_basis()
    
    def pnl_percentage(self) -> float:
        """Calculate total unrealized P&L as percentage."""
        basis = self.total_cost_basis()
        if basis == 0:
            return 0.0
        return (self.unrealized_pnl() / basis) * 100
    
    def allocation(self) -> dict[str, float]:
        """Get current allocation percentages."""
        total_value = self.total_current_value()
        if total_value == 0:
            return {}
        
        allocation: dict[str, float] = {}
        for asset_key, holding in self.holdings.items():
            price = self.get_latest_price(holding.asset)
            if price:
                value = holding.current_value(price)
                allocation[asset_key] = (value / total_value) * 100
        
        return allocation
    
    def rebalancing_recommendation(self) -> dict[str, dict]:
        """Generate rebalancing recommendations based on target allocation."""
        if not self.rebalance_target:
            return {}
        
        current_allocation = self.allocation()
        total_value = self.total_current_value()
        recommendations: dict[str, dict] = {}
        
        for asset_key, target_percent in self.rebalance_target.items():
            current_percent = current_allocation.get(asset_key, 0.0)
            difference = target_percent - current_percent
            
            if abs(difference) > 0.5:  # Only recommend if difference > 0.5%
                target_value = (target_percent / 100) * total_value
                current_value = (current_percent / 100) * total_value
                change_needed = target_value - current_value
                
                holding = self.holdings.get(asset_key)
                if holding:
                    price = self.get_latest_price(holding.asset)
                    quantity_change = change_needed / price if price else 0
                    
                    recommendations[asset_key] = {
                        "current_percent": current_percent,
                        "target_percent": target_percent,
                        "difference": difference,
                        "current_value": current_value,
                        "target_value": target_value,
                        "quantity_change": quantity_change,
                        "action": "buy" if difference > 0 else "sell",
                    }
        
        return recommendations
    
    def to_dict(self) -> dict:
        """Convert portfolio to dictionary."""
        return {
            "portfolio_id": self.portfolio_id,
            "owner_name": self.owner_name,
            "created_at": self.created_at.isoformat(),
            "holding_count": len(self.holdings),
            "total_cost_basis": self.total_cost_basis(),
            "total_current_value": self.total_current_value(),
            "unrealized_pnl": self.unrealized_pnl(),
            "pnl_percentage": self.pnl_percentage(),
        }


@dataclass
class Trade:
    """A cryptocurrency trade transaction.
    
    Attributes:
        trade_id: Unique trade identifier
        portfolio_id: Associated portfolio
        asset: Cryptocurrency asset
        action: BUY or SELL
        quantity: Amount traded
        price_usd: Price per unit at trade time
        timestamp: When trade was executed
        exchange: Trading exchange
        reference_id: External reference (order ID, hash, etc.)
        notes: Trade notes or rationale
    """
    portfolio_id: str
    asset: CryptoAsset
    action: str  # "buy" or "sell"
    quantity: float
    price_usd: float
    timestamp: datetime
    trade_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    exchange: str = "manual"
    reference_id: Optional[str] = None
    notes: str = ""
    
    def __post_init__(self):
        """Validate trade data."""
        if self.quantity <= 0:
            raise ValueError(f"Quantity must be positive, got {self.quantity}")
        if self.price_usd <= 0:
            raise ValueError(f"Price must be positive, got {self.price_usd}")
        if self.action not in ["buy", "sell"]:
            raise ValueError(f"Action must be 'buy' or 'sell', got {self.action}")
        if not isinstance(self.timestamp, datetime):
            raise ValueError("timestamp must be a datetime object")
        if self.timestamp.tzinfo is None:
            raise ValueError("timestamp must be timezone-aware (UTC)")
    
    def total_usd(self) -> float:
        """Calculate total transaction value in USD."""
        return self.quantity * self.price_usd
    
    def to_dict(self) -> dict:
        """Convert trade to dictionary."""
        return {
            "trade_id": self.trade_id,
            "portfolio_id": self.portfolio_id,
            "asset": self.asset.value,
            "action": self.action,
            "quantity": self.quantity,
            "price_usd": self.price_usd,
            "total_usd": self.total_usd(),
            "timestamp": self.timestamp.isoformat(),
            "exchange": self.exchange,
            "reference_id": self.reference_id,
            "notes": self.notes,
        }


class PortfolioManager:
    """Manager for persistent portfolio storage and retrieval."""
    
    def __init__(self, data_dir: Optional[Path] = None):
        """Initialize portfolio manager.
        
        Args:
            data_dir: Directory for portfolio persistence (defaults to D:/jarvis-data/portfolios/)
        """
        if data_dir is None:
            data_dir = Path("D:/jarvis-data/portfolios")
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.portfolios: dict[str, Portfolio] = {}
    
    def create_portfolio(self, owner_name: str) -> Portfolio:
        """Create a new portfolio."""
        portfolio_id = str(uuid.uuid4())
        portfolio = Portfolio(
            portfolio_id=portfolio_id,
            owner_name=owner_name,
            created_at=datetime.now(timezone.utc),
        )
        self.portfolios[portfolio_id] = portfolio
        self.save_portfolio(portfolio)
        return portfolio
    
    def get_portfolio(self, portfolio_id: str) -> Optional[Portfolio]:
        """Retrieve a portfolio by ID."""
        if portfolio_id in self.portfolios:
            return self.portfolios[portfolio_id]
        
        return self.load_portfolio(portfolio_id)
    
    def list_portfolios(self) -> list[Portfolio]:
        """List all portfolios."""
        return list(self.portfolios.values())
    
    def save_portfolio(self, portfolio: Portfolio) -> Path:
        """Persist portfolio to JSON file."""
        portfolio_file = self.data_dir / f"{portfolio.portfolio_id}.json"
        
        # Serialize portfolio with all holdings and price history
        data = {
            "portfolio_id": portfolio.portfolio_id,
            "owner_name": portfolio.owner_name,
            "created_at": portfolio.created_at.isoformat(),
            "rebalance_target": portfolio.rebalance_target,
            "holdings": {
                asset_key: {
                    "asset": holding.asset.value,
                    "quantity": holding.quantity,
                    "average_cost_usd": holding.average_cost_usd,
                    "cost_basis": holding.cost_basis(),
                    "purchased_at": holding.purchased_at.isoformat(),
                    "metadata": holding.metadata,
                }
                for asset_key, holding in portfolio.holdings.items()
            },
            "price_history": {
                asset_key: [quote.to_dict() for quote in quotes]
                for asset_key, quotes in portfolio.price_history.items()
            }
        }
        
        with open(portfolio_file, "w") as f:
            json.dump(data, f, indent=2)
        
        return portfolio_file
    
    def load_portfolio(self, portfolio_id: str) -> Optional[Portfolio]:
        """Load a portfolio from JSON file."""
        portfolio_file = self.data_dir / f"{portfolio_id}.json"
        
        if not portfolio_file.exists():
            return None
        
        with open(portfolio_file, "r") as f:
            data = json.load(f)
        
        portfolio = Portfolio(
            portfolio_id=data["portfolio_id"],
            owner_name=data["owner_name"],
            created_at=datetime.fromisoformat(data["created_at"]),
            rebalance_target=data.get("rebalance_target", {}),
        )
        
        # Load holdings
        for asset_key, holding_data in data.get("holdings", {}).items():
            # Parse timestamps and ensure UTC timezone
            purchased_at = datetime.fromisoformat(holding_data["purchased_at"])
            if purchased_at.tzinfo is None:
                purchased_at = purchased_at.replace(tzinfo=timezone.utc)
            
            holding = Holding(
                asset=CryptoAsset(holding_data["asset"]),
                quantity=holding_data["quantity"],
                average_cost_usd=holding_data["average_cost_usd"],
                purchased_at=purchased_at,
                metadata=holding_data.get("metadata", {}),
            )
            portfolio.holdings[asset_key] = holding
        
        # Load price history
        for asset_key, quotes_data in data.get("price_history", {}).items():
            quotes = []
            for quote_data in quotes_data:
                ts = datetime.fromisoformat(quote_data["timestamp"])
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                
                quote = PriceQuote(
                    asset=CryptoAsset(quote_data["asset"]),
                    price_usd=quote_data["price_usd"],
                    timestamp=ts,
                    source=quote_data.get("source", "manual"),
                    market_cap_usd=quote_data.get("market_cap_usd"),
                    volume_24h_usd=quote_data.get("volume_24h_usd"),
                    change_24h_percent=quote_data.get("change_24h_percent"),
                )
                quotes.append(quote)
            
            portfolio.price_history[asset_key] = quotes
        
        # Cache in memory
        self.portfolios[portfolio_id] = portfolio
        return portfolio


def get_portfolio_summary(portfolio: Portfolio) -> dict:
    """Generate a summary of portfolio status."""
    return {
        "portfolio_id": portfolio.portfolio_id,
        "owner": portfolio.owner_name,
        "holding_count": len(portfolio.holdings),
        "total_cost_basis": portfolio.total_cost_basis(),
        "total_current_value": portfolio.total_current_value(),
        "unrealized_pnl": portfolio.unrealized_pnl(),
        "pnl_percentage": portfolio.pnl_percentage(),
        "allocation": portfolio.allocation(),
        "rebalancing_needed": bool(portfolio.rebalancing_recommendation()),
    }
