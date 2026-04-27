"""Gold (XAUUSD) trade execution with sentiment context."""

from datetime import datetime, timezone
from typing import Optional
from dataclasses import dataclass
import json
from pathlib import Path


@dataclass
class GoldTradeSignal:
    """Signal to execute a gold trade based on price and sentiment."""
    
    action: str  # "BUY" or "SELL"
    price: float  # Current gold price in USD
    quantity: float  # Ounces of gold (or contract multiplier)
    confidence: float  # Signal confidence 0.0-1.0
    reason: str  # Brief rationale
    news_sentiment: float  # -2.0 to 2.0 from news analysis
    youtube_sentiment: float  # -2.0 to 2.0 from YouTube analysis
    timestamp: str  # ISO8601 timestamp


@dataclass
class GoldTradeExecution:
    """Record of a gold trade execution."""
    
    id: str  # Unique trade ID
    signal: GoldTradeSignal
    mode: str  # "dry_run" or "live"
    status: str  # "pending", "executed", "failed"
    fill_price: Optional[float] = None  # Actual fill price
    fill_quantity: Optional[float] = None  # Actual filled quantity
    error_message: Optional[str] = None
    executed_at: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Serialize to dict."""
        return {
            "id": self.id,
            "action": self.signal.action,
            "price": self.signal.price,
            "quantity": self.signal.quantity,
            "confidence": self.signal.confidence,
            "reason": self.signal.reason,
            "news_sentiment": self.signal.news_sentiment,
            "youtube_sentiment": self.signal.youtube_sentiment,
            "mode": self.mode,
            "status": self.status,
            "fill_price": self.fill_price,
            "fill_quantity": self.fill_quantity,
            "error_message": self.error_message,
            "timestamp": self.signal.timestamp,
            "executed_at": self.executed_at,
        }


class GoldTradeDecisionEngine:
    """Logic to generate trade signals based on price and sentiment."""
    
    def __init__(
        self,
        news_sentiment_weight: float = 0.4,
        youtube_sentiment_weight: float = 0.3,
        price_momentum_weight: float = 0.3,
        min_confidence: float = 0.6,
    ):
        """Initialize decision engine with weighting parameters."""
        self.news_sentiment_weight = news_sentiment_weight
        self.youtube_sentiment_weight = youtube_sentiment_weight
        self.price_momentum_weight = price_momentum_weight
        self.min_confidence = min_confidence
    
    def generate_signal(
        self,
        current_price: float,
        previous_price: Optional[float] = None,
        news_sentiment: float = 0.0,
        youtube_sentiment: float = 0.0,
    ) -> Optional[GoldTradeSignal]:
        """
        Generate a trade signal from price and sentiment data.
        
        Args:
            current_price: Current gold price in USD per ounce
            previous_price: Previous gold price (used for momentum)
            news_sentiment: News sentiment score (-2.0 to 2.0)
            youtube_sentiment: YouTube sentiment score (-2.0 to 2.0)
            
        Returns:
            GoldTradeSignal if confidence meets threshold, otherwise None
        """
        # Clamp sentiment scores to valid range
        news_sentiment = max(-2.0, min(2.0, news_sentiment))
        youtube_sentiment = max(-2.0, min(2.0, youtube_sentiment))
        
        # Calculate average sentiment
        avg_sentiment = (news_sentiment + youtube_sentiment) / 2.0
        
        # Calculate price momentum (0.0-1.0, normalized)
        momentum_score = 0.0
        if previous_price and previous_price > 0:
            price_change_pct = (current_price - previous_price) / previous_price
            # Upward momentum: positive price change
            # Downward momentum: negative price change
            momentum_score = max(-1.0, min(1.0, price_change_pct * 10.0))  # Scale for sensitivity
        
        # Normalize sentiment to 0.0-1.0 range for weighting
        sentiment_normalized = (avg_sentiment + 2.0) / 4.0  # -2 -> 0, 2 -> 1
        momentum_normalized = (momentum_score + 1.0) / 2.0  # -1 -> 0, 1 -> 1
        
        # Calculate weighted confidence
        weighted_score = (
            sentiment_normalized * self.news_sentiment_weight +
            sentiment_normalized * self.youtube_sentiment_weight +
            momentum_normalized * self.price_momentum_weight
        ) / (self.news_sentiment_weight + self.youtube_sentiment_weight + self.price_momentum_weight)
        
        # Determine action and confidence
        if avg_sentiment > 0.5:  # Bullish
            action = "BUY"
            confidence = min(weighted_score, 0.95)
            reason = f"Bullish sentiment ({avg_sentiment:.2f}), momentum ({momentum_score:.2f})"
        elif avg_sentiment < -0.5:  # Bearish
            action = "SELL"
            confidence = min(abs(weighted_score - 1.0), 0.95)
            reason = f"Bearish sentiment ({avg_sentiment:.2f}), momentum ({momentum_score:.2f})"
        else:  # Neutral
            return None
        
        # Filter by minimum confidence
        if confidence < self.min_confidence:
            return None
        
        # Generate signal
        return GoldTradeSignal(
            action=action,
            price=current_price,
            quantity=1.0,  # 1 ounce (can be scaled by account size)
            confidence=round(confidence, 3),
            reason=reason,
            news_sentiment=round(news_sentiment, 3),
            youtube_sentiment=round(youtube_sentiment, 3),
            timestamp=datetime.now(timezone.utc).isoformat(),
        )


def execute_gold_trade_dry_run(signal: GoldTradeSignal) -> GoldTradeExecution:
    """
    Simulate gold trade execution (no actual orders).
    
    Args:
        signal: Trade signal to execute
        
    Returns:
        GoldTradeExecution record
    """
    import uuid
    
    trade_id = str(uuid.uuid4())[:12]
    
    execution = GoldTradeExecution(
        id=trade_id,
        signal=signal,
        mode="dry_run",
        status="executed",
        fill_price=signal.price,
        fill_quantity=signal.quantity,
        executed_at=datetime.now(timezone.utc).isoformat(),
    )
    
    return execution


def execute_gold_trade_live(signal: GoldTradeSignal, broker_api_key: Optional[str] = None) -> GoldTradeExecution:
    """
    Execute live gold trade via broker API (stub for future implementation).
    
    Args:
        signal: Trade signal to execute
        broker_api_key: API key for broker (e.g., Alpaca, Interactive Brokers)
        
    Returns:
        GoldTradeExecution record
        
    Raises:
        RuntimeError: If API key not provided or API call fails
    """
    import uuid
    
    if not broker_api_key:
        raise RuntimeError("Live gold trade execution requires JARVIS_BROKER_API_KEY")
    
    trade_id = str(uuid.uuid4())[:12]
    
    # TODO: Integrate with broker API
    # For example, with Alpaca:
    # would call: POST /v2/orders with order details
    # would handle: order confirmation, fills, rejections
    
    raise RuntimeError("Live gold trade execution not yet implemented")


def execute_gold_trade(
    signal: GoldTradeSignal,
    mode: str = "dry_run",
    broker_api_key: Optional[str] = None,
) -> GoldTradeExecution:
    """
    Unified gold trade execution supporting dry_run and live modes.
    
    Args:
        signal: Trade signal to execute
        mode: "dry_run" or "live"
        broker_api_key: API key for live mode
        
    Returns:
        GoldTradeExecution record
        
    Raises:
        RuntimeError: If live mode requested but API not available
        ValueError: If invalid mode
    """
    if mode == "dry_run":
        return execute_gold_trade_dry_run(signal)
    elif mode == "live":
        return execute_gold_trade_live(signal, broker_api_key=broker_api_key)
    else:
        raise ValueError(f"Unknown gold trade mode: {mode}")


def log_gold_trade_execution(
    execution: GoldTradeExecution,
    trades_log_path: Path,
) -> None:
    """
    Append trade execution record to trades log.
    
    Args:
        execution: Trade execution to log
        trades_log_path: Path to trades log file
    """
    trades_log_path.parent.mkdir(parents=True, exist_ok=True)
    
    record = execution.to_dict()
    record["ts"] = datetime.now(timezone.utc).timestamp()
    
    with trades_log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, sort_keys=True) + "\n")


class GoldTradeJournal:
    """Track gold trades with metadata and performance metrics."""
    
    def __init__(self, trades_log_path: Path):
        self.trades_log_path = Path(trades_log_path)
        self.trades: list[GoldTradeExecution] = []
    
    def load(self) -> None:
        """Load trades from log file."""
        self.trades.clear()
        
        if not self.trades_log_path.exists():
            return
        
        with self.trades_log_path.open("r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                    # Parse back to GoldTradeExecution (simplified)
                    # In production, would reconstruct with proper signal object
                    self.trades.append(record)
                except json.JSONDecodeError:
                    pass
    
    def add_execution(self, execution: GoldTradeExecution) -> None:
        """Add execution record to journal."""
        self.trades.append(execution.to_dict())
        log_gold_trade_execution(execution, self.trades_log_path)
    
    def performance_summary(self) -> dict:
        """Calculate performance metrics across all trades."""
        if not self.trades:
            return {
                "count": 0,
                "buy_count": 0,
                "sell_count": 0,
                "win_count": 0,
                "loss_count": 0,
                "win_rate": 0.0,
                "total_pnl": 0.0,
                "avg_confidence": 0.0,
            }
        
        buy_count = sum(1 for t in self.trades if isinstance(t, dict) and t.get("action") == "BUY")
        sell_count = sum(1 for t in self.trades if isinstance(t, dict) and t.get("action") == "SELL")
        
        # Win rate based on executed status
        executed = [t for t in self.trades if isinstance(t, dict) and t.get("status") == "executed"]
        win_count = len([t for t in executed if t.get("confidence", 0.0) > 0.7])
        loss_count = len(executed) - win_count
        win_rate = win_count / len(executed) if executed else 0.0
        
        # Average confidence
        confidences = [t.get("confidence", 0.5) for t in self.trades if isinstance(t, dict)]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
        return {
            "count": len(self.trades),
            "buy_count": buy_count,
            "sell_count": sell_count,
            "win_count": win_count,
            "loss_count": loss_count,
            "win_rate": round(win_rate, 3),
            "total_pnl": 0.0,  # Would calculate from fill prices
            "avg_confidence": round(avg_confidence, 3),
        }
