"""News sentiment ingestion and analysis."""

from datetime import datetime, timedelta, timezone
from typing import Optional
from enum import Enum
import hashlib


class SentimentLabel(str, Enum):
    """Sentiment classification."""
    VERY_POSITIVE = "very_positive"  # +2
    POSITIVE = "positive"            # +1
    NEUTRAL = "neutral"              # 0
    NEGATIVE = "negative"            # -1
    VERY_NEGATIVE = "very_negative"  # -2


def score_from_label(label: SentimentLabel) -> int:
    """Convert sentiment label to numeric score."""
    scores = {
        SentimentLabel.VERY_POSITIVE: 2,
        SentimentLabel.POSITIVE: 1,
        SentimentLabel.NEUTRAL: 0,
        SentimentLabel.NEGATIVE: -1,
        SentimentLabel.VERY_NEGATIVE: -2,
    }
    return scores.get(label, 0)


def parse_sentiment_label(raw_label: str) -> SentimentLabel:
    """Parse string into sentiment label with fallback to neutral."""
    normalized = raw_label.lower().strip()
    for label in SentimentLabel:
        if label.value == normalized:
            return label
    return SentimentLabel.NEUTRAL


class NewsItem:
    """Single news article with sentiment metadata."""
    
    def __init__(
        self,
        title: str,
        source: str,
        timestamp: str,
        sentiment: SentimentLabel,
        relevance: float = 0.8,
        url: Optional[str] = None,
        summary: Optional[str] = None,
    ):
        self.id = self._compute_id(title, source)
        self.title = title
        self.source = source
        self.timestamp = timestamp
        self.sentiment = sentiment if isinstance(sentiment, SentimentLabel) else parse_sentiment_label(str(sentiment))
        self.relevance = max(0.0, min(1.0, relevance))  # Clamp 0..1
        self.url = url
        self.summary = summary
    
    @staticmethod
    def _compute_id(title: str, source: str) -> str:
        """Deterministic hash ID for deduplication."""
        key = f"{title}:{source}".encode("utf-8")
        return hashlib.sha256(key).hexdigest()[:16]
    
    def to_dict(self) -> dict:
        """Serialize to dict for audit/storage."""
        return {
            "id": self.id,
            "title": self.title,
            "source": self.source,
            "timestamp": self.timestamp,
            "sentiment": self.sentiment.value,
            "relevance": self.relevance,
            "url": self.url,
            "summary": self.summary,
        }


class NewsFeed:
    """Collection of news items with aggregated sentiment."""
    
    def __init__(self, items: list[NewsItem]):
        self.items = items
        self._deduplicate()
    
    def _deduplicate(self):
        """Remove duplicate items by ID, keeping first occurrence."""
        seen = set()
        unique = []
        for item in self.items:
            if item.id not in seen:
                seen.add(item.id)
                unique.append(item)
        self.items = unique
    
    def aggregate_sentiment(self) -> dict:
        """Compute aggregate sentiment metrics across all items."""
        if not self.items:
            return {
                "count": 0,
                "weighted_sentiment": 0.0,
                "sentiment_distribution": {
                    "very_positive": 0,
                    "positive": 0,
                    "neutral": 0,
                    "negative": 0,
                    "very_negative": 0,
                }
            }
        
        # Count and weight by relevance
        total_weight = 0.0
        weighted_sum = 0.0
        distribution = {label.value: 0 for label in SentimentLabel}
        
        for item in self.items:
            score = score_from_label(item.sentiment)
            weight = item.relevance
            
            weighted_sum += score * weight
            total_weight += weight
            distribution[item.sentiment.value] += 1
        
        weighted_sentiment = weighted_sum / total_weight if total_weight > 0 else 0.0
        
        return {
            "count": len(self.items),
            "weighted_sentiment": round(weighted_sentiment, 3),
            "sentiment_distribution": distribution,
        }
    
    def filter_by_source(self, source: str) -> "NewsFeed":
        """Filter items by news source."""
        filtered = [item for item in self.items if item.source.lower() == source.lower()]
        return NewsFeed(filtered)
    
    def filter_by_sentiment(self, min_score: int, max_score: int) -> "NewsFeed":
        """Filter items by sentiment score range."""
        filtered = [
            item for item in self.items
            if min_score <= score_from_label(item.sentiment) <= max_score
        ]
        return NewsFeed(filtered)
    
    def to_dict(self) -> dict:
        """Serialize to dict."""
        return {
            "items": [item.to_dict() for item in self.items],
            "metrics": self.aggregate_sentiment(),
        }


def ingest_news_dry_run(query: str = "gold market") -> NewsFeed:
    """
    Return deterministic mock news feed for testing.
    
    Args:
        query: Search query (unused in dry-run, for API compatibility)
        
    Returns:
        NewsFeed with mock items
    """
    now = datetime.now(timezone.utc)
    
    items = [
        NewsItem(
            title="Gold prices rise amid inflation concerns",
            source="Bloomberg",
            timestamp=(now - timedelta(hours=2)).isoformat(),
            sentiment=SentimentLabel.POSITIVE,
            relevance=0.95,
            url="https://example.com/gold-price-rise",
            summary="Gold edges higher as inflation data disappoints."
        ),
        NewsItem(
            title="Federal Reserve holds rates steady",
            source="Reuters",
            timestamp=(now - timedelta(hours=4)).isoformat(),
            sentiment=SentimentLabel.NEUTRAL,
            relevance=0.8,
            url="https://example.com/fed-holds-rates",
            summary="Central bank maintains current policy stance."
        ),
        NewsItem(
            title="Risk-off sentiment boosts safe havens",
            source="MarketWatch",
            timestamp=(now - timedelta(hours=1)).isoformat(),
            sentiment=SentimentLabel.POSITIVE,
            relevance=0.85,
            url="https://example.com/safe-havens",
            summary="Gold and bonds benefit from market uncertainty."
        ),
    ]
    
    return NewsFeed(items)


def ingest_news_live(query: str, api_key: Optional[str] = None) -> NewsFeed:
    """
    Fetch live news feed from external API (stub for future implementation).
    
    Current implementation: returns error prompting for API key.
    
    Args:
        query: Search query for news
        api_key: API key for news service (e.g., NewsAPI, Alpha Vantage)
        
    Returns:
        NewsFeed with live items
        
    Raises:
        RuntimeError: If API key not configured or API call fails
    """
    if not api_key:
        raise RuntimeError("Live news ingestion requires JARVIS_NEWS_API_KEY")
    
    # TODO: Integrate with NewsAPI.org or Alpha Vantage sentiment endpoint
    # For now, placeholder that would call:
    # response = httpx.get(f"https://newsapi.org/v2/everything?q={query}&sortBy=publishedAt")
    raise RuntimeError("Live news ingestion not yet implemented")


def get_news_sentiment(
    query: str = "gold market",
    mode: str = "dry_run",
    api_key: Optional[str] = None,
) -> dict:
    """
    Unified news sentiment getter supporting dry_run and live modes.
    
    Args:
        query: Search query for news
        mode: "dry_run" or "live"
        api_key: API key for live mode
        
    Returns:
        Dict with feed data and aggregate sentiment metrics
        
    Raises:
        RuntimeError: If live mode requested but API not available
        ValueError: If invalid mode
    """
    if mode == "dry_run":
        feed = ingest_news_dry_run(query)
    elif mode == "live":
        feed = ingest_news_live(query, api_key=api_key)
    else:
        raise ValueError(f"Unknown news sentiment mode: {mode}")
    
    result = feed.to_dict()
    result["ok"] = True
    result["mode"] = mode
    result["timestamp"] = datetime.now(timezone.utc).isoformat()
    return result
