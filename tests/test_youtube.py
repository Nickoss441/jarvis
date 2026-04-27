"""Tests for YouTube sentiment analysis module."""

import pytest
from jarvis.tools.youtube import (
    YouTubeSentimentLabel,
    YouTubeComment,
    YouTubeCommentThread,
    youtube_sentiment_score,
    ingest_youtube_comments_dry_run,
    ingest_youtube_comments_live,
    get_youtube_sentiment,
)


class TestYouTubeSentimentLabel:
    """Test YouTube sentiment label enum."""
    
    def test_sentiment_label_values(self):
        """All labels have expected string values."""
        assert YouTubeSentimentLabel.VERY_POSITIVE.value == "very_positive"
        assert YouTubeSentimentLabel.POSITIVE.value == "positive"
        assert YouTubeSentimentLabel.NEUTRAL.value == "neutral"
        assert YouTubeSentimentLabel.NEGATIVE.value == "negative"
        assert YouTubeSentimentLabel.VERY_NEGATIVE.value == "very_negative"


class TestYouTubeSentimentScoring:
    """Test YouTube sentiment score conversion."""
    
    def test_youtube_sentiment_score(self):
        """Labels map to correct numeric scores."""
        assert youtube_sentiment_score(YouTubeSentimentLabel.VERY_POSITIVE) == 2
        assert youtube_sentiment_score(YouTubeSentimentLabel.POSITIVE) == 1
        assert youtube_sentiment_score(YouTubeSentimentLabel.NEUTRAL) == 0
        assert youtube_sentiment_score(YouTubeSentimentLabel.NEGATIVE) == -1
        assert youtube_sentiment_score(YouTubeSentimentLabel.VERY_NEGATIVE) == -2


class TestYouTubeComment:
    """Test individual YouTube comment."""
    
    def test_comment_creation(self):
        """YouTubeComment initializes with all fields."""
        comment = YouTubeComment(
            author="TestUser",
            text="Great video!",
            sentiment=YouTubeSentimentLabel.POSITIVE,
            likes=10,
            video_id="vid123"
        )
        
        assert comment.author == "TestUser"
        assert comment.text == "Great video!"
        assert comment.sentiment == YouTubeSentimentLabel.POSITIVE
        assert comment.likes == 10
        assert comment.video_id == "vid123"
    
    def test_comment_id_deterministic(self):
        """Same author+text always produces same ID."""
        comment1 = YouTubeComment("User", "Text", YouTubeSentimentLabel.POSITIVE, likes=5)
        comment2 = YouTubeComment("User", "Text", YouTubeSentimentLabel.NEGATIVE, likes=20)
        
        assert comment1.id == comment2.id
    
    def test_comment_id_different_for_different_content(self):
        """Different author or text produces different ID."""
        comment1 = YouTubeComment("User1", "Text", YouTubeSentimentLabel.POSITIVE)
        comment2 = YouTubeComment("User2", "Text", YouTubeSentimentLabel.POSITIVE)
        
        assert comment1.id != comment2.id
    
    def test_comment_likes_non_negative(self):
        """Likes are clamped to non-negative."""
        comment = YouTubeComment("User", "Text", YouTubeSentimentLabel.NEUTRAL, likes=-5)
        assert comment.likes == 0
    
    def test_comment_to_dict(self):
        """Serialization preserves all fields."""
        comment = YouTubeComment("User", "Text", YouTubeSentimentLabel.POSITIVE, likes=15)
        result = comment.to_dict()
        
        assert result["author"] == "User"
        assert result["text"] == "Text"
        assert result["sentiment"] == "positive"
        assert result["likes"] == 15


class TestYouTubeCommentThread:
    """Test comment thread aggregation."""
    
    def test_thread_deduplication(self):
        """Duplicate comments (same ID) are removed."""
        comment1 = YouTubeComment("User", "Text", YouTubeSentimentLabel.POSITIVE, likes=5)
        comment2 = YouTubeComment("User", "Text", YouTubeSentimentLabel.NEGATIVE, likes=10)
        comment3 = YouTubeComment("Other", "Different", YouTubeSentimentLabel.NEUTRAL, likes=3)
        
        thread = YouTubeCommentThread("vid123", "Test Video", [comment1, comment2, comment3])
        
        assert len(thread.comments) == 2  # comment1 and comment2 are duplicates
    
    def test_aggregate_sentiment_empty_thread(self):
        """Empty thread returns zero sentiment."""
        thread = YouTubeCommentThread("vid123", "Test Video", [])
        result = thread.aggregate_sentiment()
        
        assert result["count"] == 0
        assert result["weighted_sentiment"] == 0.0
        assert result["total_engagement"] == 0
    
    def test_aggregate_sentiment_single_comment(self):
        """Single comment thread reflects that comment's sentiment."""
        comment = YouTubeComment("User", "Text", YouTubeSentimentLabel.POSITIVE, likes=50)
        thread = YouTubeCommentThread("vid123", "Test", [comment])
        result = thread.aggregate_sentiment()
        
        assert result["count"] == 1
        assert result["total_engagement"] == 50
        assert result["avg_engagement_per_comment"] == 50.0
        # weighted_sentiment = (1 * (1 + 50/100)) / (1 + 0.5) = 1.5 / 1.5 = 1.0
        assert result["weighted_sentiment"] == 1.0
    
    def test_aggregate_sentiment_weighted_by_engagement(self):
        """Sentiment is weighted by comment engagement (likes)."""
        comment1 = YouTubeComment("User1", "Positive with lots of likes", YouTubeSentimentLabel.POSITIVE, likes=100)
        comment2 = YouTubeComment("User2", "Negative with few likes", YouTubeSentimentLabel.NEGATIVE, likes=1)
        thread = YouTubeCommentThread("vid123", "Test", [comment1, comment2])
        result = thread.aggregate_sentiment()
        
        assert result["weighted_sentiment"] > 0  # Should favor the popular positive comment
        assert result["count"] == 2
        assert result["total_engagement"] == 101
    
    def test_aggregate_sentiment_distribution(self):
        """Sentiment distribution counts each sentiment type."""
        comments = [
            YouTubeComment(f"User{i}", f"Text{i}", sentiment)
            for i, sentiment in enumerate([
                YouTubeSentimentLabel.VERY_POSITIVE,
                YouTubeSentimentLabel.POSITIVE,
                YouTubeSentimentLabel.NEUTRAL,
                YouTubeSentimentLabel.NEGATIVE,
                YouTubeSentimentLabel.VERY_NEGATIVE,
            ])
        ]
        thread = YouTubeCommentThread("vid123", "Test", comments)
        result = thread.aggregate_sentiment()
        
        distribution = result["sentiment_distribution"]
        assert distribution["very_positive"] == 1
        assert distribution["positive"] == 1
        assert distribution["neutral"] == 1
        assert distribution["negative"] == 1
        assert distribution["very_negative"] == 1


class TestDryRunIngest:
    """Test mock YouTube comment ingestion."""
    
    def test_dry_run_returns_thread(self):
        """Dry-run always returns valid thread."""
        thread = ingest_youtube_comments_dry_run()
        
        assert isinstance(thread, YouTubeCommentThread)
        assert len(thread.comments) > 0
        assert all(isinstance(comment, YouTubeComment) for comment in thread.comments)
    
    def test_dry_run_has_metrics(self):
        """Dry-run thread has sentiment metrics."""
        thread = ingest_youtube_comments_dry_run()
        metrics = thread.aggregate_sentiment()
        
        assert "count" in metrics
        assert "weighted_sentiment" in metrics
        assert "total_engagement" in metrics
        assert "sentiment_distribution" in metrics
    
    def test_dry_run_video_id_included(self):
        """Dry-run respects provided video_id."""
        thread = ingest_youtube_comments_dry_run(video_id="test123")
        
        assert thread.video_id == "test123"
        assert all(comment.video_id == "test123" for comment in thread.comments)


class TestLiveIngest:
    """Test live YouTube comment ingestion."""
    
    def test_live_without_api_key_raises(self):
        """Live mode without API key raises error."""
        with pytest.raises(RuntimeError, match="requires JARVIS_YOUTUBE_API_KEY"):
            ingest_youtube_comments_live("video_id", api_key=None)
    
    def test_live_with_api_key_not_yet_implemented(self):
        """Live mode with API key raises not-implemented error."""
        with pytest.raises(RuntimeError, match="not yet implemented"):
            ingest_youtube_comments_live("video_id", api_key="test-key")


class TestGetYouTubeSentiment:
    """Test unified YouTube sentiment getter."""
    
    def test_get_dry_run_mode(self):
        """Unified getter supports dry_run mode."""
        result = get_youtube_sentiment(mode="dry_run")
        
        assert result["ok"] is True
        assert result["mode"] == "dry_run"
        assert "timestamp" in result
        assert "metrics" in result
        assert "comments" in result
    
    def test_get_with_custom_video_id(self):
        """Custom video ID is accepted (even if unused in dry-run)."""
        result = get_youtube_sentiment(video_id="custom_id", mode="dry_run")
        
        assert result["ok"] is True
        assert result["video_id"] == "custom_id"
    
    def test_get_invalid_mode_raises(self):
        """Invalid mode raises ValueError."""
        with pytest.raises(ValueError, match="Unknown YouTube sentiment mode"):
            get_youtube_sentiment(mode="invalid")
    
    def test_get_live_without_api_key_raises(self):
        """Live mode without API key raises error."""
        with pytest.raises(RuntimeError, match="requires JARVIS_YOUTUBE_API_KEY"):
            get_youtube_sentiment(mode="live", api_key=None)
