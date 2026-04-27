"""Tests for news sentiment ingestion module."""

import pytest
from datetime import datetime, timedelta, timezone
from jarvis.tools.news import (
    SentimentLabel,
    NewsItem,
    NewsFeed,
    score_from_label,
    parse_sentiment_label,
    ingest_news_dry_run,
    ingest_news_live,
    get_news_sentiment,
)


class TestSentimentLabel:
    """Test sentiment label enum."""
    
    def test_sentiment_label_values(self):
        """All labels have expected string values."""
        assert SentimentLabel.VERY_POSITIVE.value == "very_positive"
        assert SentimentLabel.POSITIVE.value == "positive"
        assert SentimentLabel.NEUTRAL.value == "neutral"
        assert SentimentLabel.NEGATIVE.value == "negative"
        assert SentimentLabel.VERY_NEGATIVE.value == "very_negative"


class TestSentimentScoring:
    """Test sentiment score conversion."""
    
    def test_score_from_label(self):
        """Labels map to correct numeric scores."""
        assert score_from_label(SentimentLabel.VERY_POSITIVE) == 2
        assert score_from_label(SentimentLabel.POSITIVE) == 1
        assert score_from_label(SentimentLabel.NEUTRAL) == 0
        assert score_from_label(SentimentLabel.NEGATIVE) == -1
        assert score_from_label(SentimentLabel.VERY_NEGATIVE) == -2
    
    def test_parse_sentiment_label_valid(self):
        """Valid sentiment strings parse correctly."""
        assert parse_sentiment_label("positive") == SentimentLabel.POSITIVE
        assert parse_sentiment_label("NEUTRAL") == SentimentLabel.NEUTRAL
        assert parse_sentiment_label(" negative ") == SentimentLabel.NEGATIVE
    
    def test_parse_sentiment_label_invalid_defaults_neutral(self):
        """Unknown sentiment strings default to neutral."""
        assert parse_sentiment_label("unknown") == SentimentLabel.NEUTRAL
        assert parse_sentiment_label("bullish") == SentimentLabel.NEUTRAL


class TestNewsItem:
    """Test individual news article."""
    
    def test_news_item_creation(self):
        """NewsItem initializes with all fields."""
        item = NewsItem(
            title="Test Article",
            source="Reuters",
            timestamp="2026-04-27T10:00:00Z",
            sentiment=SentimentLabel.POSITIVE,
            relevance=0.9,
            url="https://example.com",
            summary="Test summary"
        )
        
        assert item.title == "Test Article"
        assert item.source == "Reuters"
        assert item.sentiment == SentimentLabel.POSITIVE
        assert item.relevance == 0.9
        assert item.url == "https://example.com"
    
    def test_news_item_id_deterministic(self):
        """Same title+source always produces same ID."""
        item1 = NewsItem("Gold rises", "Bloomberg", "2026-04-27T00:00:00Z", SentimentLabel.POSITIVE)
        item2 = NewsItem("Gold rises", "Bloomberg", "2026-04-27T01:00:00Z", SentimentLabel.NEUTRAL)
        
        assert item1.id == item2.id
    
    def test_news_item_id_different_for_different_content(self):
        """Different title or source produces different ID."""
        item1 = NewsItem("Gold rises", "Bloomberg", "2026-04-27T00:00:00Z", SentimentLabel.POSITIVE)
        item2 = NewsItem("Gold falls", "Bloomberg", "2026-04-27T00:00:00Z", SentimentLabel.NEGATIVE)
        
        assert item1.id != item2.id
    
    def test_news_item_relevance_clamped(self):
        """Relevance score is clamped to [0, 1]."""
        low = NewsItem("Test", "Source", "2026-04-27T00:00:00Z", SentimentLabel.NEUTRAL, relevance=-0.5)
        assert low.relevance == 0.0
        
        high = NewsItem("Test", "Source", "2026-04-27T00:00:00Z", SentimentLabel.NEUTRAL, relevance=1.5)
        assert high.relevance == 1.0
    
    def test_news_item_to_dict(self):
        """Serialization to dict preserves all fields."""
        item = NewsItem("Test", "Reuters", "2026-04-27T00:00:00Z", SentimentLabel.POSITIVE)
        result = item.to_dict()
        
        assert result["title"] == "Test"
        assert result["source"] == "Reuters"
        assert result["sentiment"] == "positive"
        assert "id" in result


class TestNewsFeed:
    """Test news feed aggregation."""
    
    def test_feed_deduplication(self):
        """Duplicate items (same ID) are removed."""
        item1 = NewsItem("Gold rises", "Reuters", "2026-04-27T00:00:00Z", SentimentLabel.POSITIVE)
        item2 = NewsItem("Gold rises", "Reuters", "2026-04-27T01:00:00Z", SentimentLabel.NEGATIVE)
        item3 = NewsItem("Different", "Reuters", "2026-04-27T02:00:00Z", SentimentLabel.NEUTRAL)
        
        feed = NewsFeed([item1, item2, item3])
        
        assert len(feed.items) == 2  # item1 and item2 are duplicates
        assert feed.items[0].id == item1.id
        assert feed.items[1].id == item3.id
    
    def test_aggregate_sentiment_empty_feed(self):
        """Empty feed returns zero sentiment."""
        feed = NewsFeed([])
        result = feed.aggregate_sentiment()
        
        assert result["count"] == 0
        assert result["weighted_sentiment"] == 0.0
        assert all(v == 0 for v in result["sentiment_distribution"].values())
    
    def test_aggregate_sentiment_single_item(self):
        """Single item feed reflects that item's sentiment."""
        item = NewsItem("Test", "Reuters", "2026-04-27T00:00:00Z", SentimentLabel.POSITIVE, relevance=0.8)
        feed = NewsFeed([item])
        result = feed.aggregate_sentiment()
        
        assert result["count"] == 1
        # weighted_sentiment = (score * weight) / total_weight = (1 * 0.8) / 0.8 = 1.0
        assert result["weighted_sentiment"] == 1.0
        assert result["sentiment_distribution"]["positive"] == 1
    
    def test_aggregate_sentiment_weighted(self):
        """Sentiment aggregation is weighted by relevance."""
        item1 = NewsItem("Very relevant positive", "Reuters", "2026-04-27T00:00:00Z", 
                        SentimentLabel.POSITIVE, relevance=1.0)
        item2 = NewsItem("Low relevance negative", "Reuters", "2026-04-27T01:00:00Z", 
                        SentimentLabel.NEGATIVE, relevance=0.1)
        feed = NewsFeed([item1, item2])
        result = feed.aggregate_sentiment()
        
        # (1 * 1.0 + (-1) * 0.1) / (1.0 + 0.1) = 0.9 / 1.1 ≈ 0.818
        assert result["weighted_sentiment"] > 0.8
        assert result["count"] == 2
    
    def test_filter_by_source(self):
        """Feed can be filtered by source."""
        item1 = NewsItem("Test1", "Reuters", "2026-04-27T00:00:00Z", SentimentLabel.POSITIVE)
        item2 = NewsItem("Test2", "Bloomberg", "2026-04-27T01:00:00Z", SentimentLabel.NEGATIVE)
        item3 = NewsItem("Test3", "Reuters", "2026-04-27T02:00:00Z", SentimentLabel.NEUTRAL)
        
        feed = NewsFeed([item1, item2, item3])
        reuters_feed = feed.filter_by_source("reuters")
        
        assert len(reuters_feed.items) == 2
        assert all(item.source.lower() == "reuters" for item in reuters_feed.items)
    
    def test_filter_by_sentiment(self):
        """Feed can be filtered by sentiment score range."""
        items = [
            NewsItem(f"Item{i}", "Reuters", "2026-04-27T00:00:00Z", sentiment)
            for i, sentiment in enumerate([
                SentimentLabel.VERY_POSITIVE,
                SentimentLabel.POSITIVE,
                SentimentLabel.NEUTRAL,
                SentimentLabel.NEGATIVE,
                SentimentLabel.VERY_NEGATIVE,
            ])
        ]
        feed = NewsFeed(items)
        
        # Filter for positive/neutral/negative (scores 1, 0, -1)
        positive_feed = feed.filter_by_sentiment(min_score=-1, max_score=1)
        
        assert len(positive_feed.items) == 3  # excludes very_positive (2) and very_negative (-2)


class TestDryRunIngest:
    """Test mock news ingestion."""
    
    def test_dry_run_returns_feed(self):
        """Dry-run always returns valid feed."""
        feed = ingest_news_dry_run()
        
        assert isinstance(feed, NewsFeed)
        assert len(feed.items) > 0
        assert all(isinstance(item, NewsItem) for item in feed.items)
    
    def test_dry_run_has_metrics(self):
        """Dry-run feed has sentiment metrics."""
        feed = ingest_news_dry_run()
        metrics = feed.aggregate_sentiment()
        
        assert "count" in metrics
        assert "weighted_sentiment" in metrics
        assert "sentiment_distribution" in metrics


class TestLiveIngest:
    """Test live news ingestion."""
    
    def test_live_without_api_key_raises(self):
        """Live mode without API key raises error."""
        with pytest.raises(RuntimeError, match="requires JARVIS_NEWS_API_KEY"):
            ingest_news_live("gold market", api_key=None)
    
    def test_live_with_api_key_not_yet_implemented(self):
        """Live mode with API key raises not-implemented error."""
        with pytest.raises(RuntimeError, match="not yet implemented"):
            ingest_news_live("gold market", api_key="test-key")


class TestGetNewsSentiment:
    """Test unified sentiment getter."""
    
    def test_get_dry_run_mode(self):
        """Unified getter supports dry_run mode."""
        result = get_news_sentiment(mode="dry_run")
        
        assert result["ok"] is True
        assert result["mode"] == "dry_run"
        assert "timestamp" in result
        assert "metrics" in result
        assert "items" in result
    
    def test_get_with_custom_query(self):
        """Custom query is accepted (even if unused in dry-run)."""
        result = get_news_sentiment(query="silver market", mode="dry_run")
        
        assert result["ok"] is True
    
    def test_get_invalid_mode_raises(self):
        """Invalid mode raises ValueError."""
        with pytest.raises(ValueError, match="Unknown news sentiment mode"):
            get_news_sentiment(mode="invalid")
    
    def test_get_live_without_api_key_raises(self):
        """Live mode without API key raises error."""
        with pytest.raises(RuntimeError, match="requires JARVIS_NEWS_API_KEY"):
            get_news_sentiment(mode="live", api_key=None)
