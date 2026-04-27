"""YouTube sentiment analysis from comments."""

from datetime import datetime, timezone
from typing import Optional
from enum import Enum
import hashlib


class YouTubeSentimentLabel(str, Enum):
    """Sentiment classification for YouTube comments."""
    VERY_POSITIVE = "very_positive"  # Love, must-buy, bullish
    POSITIVE = "positive"            # Good, like, bullish
    NEUTRAL = "neutral"              # Informational
    NEGATIVE = "negative"            # Dislike, concern, bearish
    VERY_NEGATIVE = "very_negative"  # Hate, scam, crash


def youtube_sentiment_score(label: YouTubeSentimentLabel) -> int:
    """Convert YouTube sentiment label to numeric score."""
    scores = {
        YouTubeSentimentLabel.VERY_POSITIVE: 2,
        YouTubeSentimentLabel.POSITIVE: 1,
        YouTubeSentimentLabel.NEUTRAL: 0,
        YouTubeSentimentLabel.NEGATIVE: -1,
        YouTubeSentimentLabel.VERY_NEGATIVE: -2,
    }
    return scores.get(label, 0)


class YouTubeComment:
    """Single YouTube comment with sentiment metadata."""
    
    def __init__(
        self,
        author: str,
        text: str,
        sentiment: YouTubeSentimentLabel,
        likes: int = 0,
        timestamp: Optional[str] = None,
        video_id: Optional[str] = None,
    ):
        self.id = self._compute_id(author, text)
        self.author = author
        self.text = text
        self.sentiment = sentiment if isinstance(sentiment, YouTubeSentimentLabel) else self._parse_sentiment(str(sentiment))
        self.likes = max(0, likes)  # Ensure non-negative
        self.timestamp = timestamp or datetime.now(timezone.utc).isoformat()
        self.video_id = video_id
    
    @staticmethod
    def _compute_id(author: str, text: str) -> str:
        """Deterministic hash ID for deduplication."""
        key = f"{author}:{text}".encode("utf-8")
        return hashlib.sha256(key).hexdigest()[:16]
    
    @staticmethod
    def _parse_sentiment(raw: str) -> YouTubeSentimentLabel:
        """Parse string to sentiment with fallback to neutral."""
        normalized = raw.lower().strip()
        for label in YouTubeSentimentLabel:
            if label.value == normalized:
                return label
        return YouTubeSentimentLabel.NEUTRAL
    
    def to_dict(self) -> dict:
        """Serialize to dict."""
        return {
            "id": self.id,
            "author": self.author,
            "text": self.text,
            "sentiment": self.sentiment.value,
            "likes": self.likes,
            "timestamp": self.timestamp,
            "video_id": self.video_id,
        }


class YouTubeCommentThread:
    """Collection of comments from a single video."""
    
    def __init__(self, video_id: str, video_title: str, comments: list[YouTubeComment]):
        self.video_id = video_id
        self.video_title = video_title
        self.comments = comments
        self._deduplicate()
    
    def _deduplicate(self):
        """Remove duplicate comments by ID, keeping first occurrence."""
        seen = set()
        unique = []
        for comment in self.comments:
            if comment.id not in seen:
                seen.add(comment.id)
                unique.append(comment)
        self.comments = unique
    
    def aggregate_sentiment(self) -> dict:
        """Compute aggregate sentiment metrics across all comments."""
        if not self.comments:
            return {
                "count": 0,
                "weighted_sentiment": 0.0,
                "total_engagement": 0,
                "sentiment_distribution": {
                    "very_positive": 0,
                    "positive": 0,
                    "neutral": 0,
                    "negative": 0,
                    "very_negative": 0,
                }
            }
        
        # Weight by engagement (likes)
        total_weight = 0.0
        weighted_sum = 0.0
        distribution = {label.value: 0 for label in YouTubeSentimentLabel}
        total_engagement = 0
        
        for comment in self.comments:
            score = youtube_sentiment_score(comment.sentiment)
            weight = 1.0 + (comment.likes / 100.0)  # Base 1 + engagement boost
            
            weighted_sum += score * weight
            total_weight += weight
            total_engagement += comment.likes
            distribution[comment.sentiment.value] += 1
        
        weighted_sentiment = weighted_sum / total_weight if total_weight > 0 else 0.0
        
        return {
            "count": len(self.comments),
            "weighted_sentiment": round(weighted_sentiment, 3),
            "total_engagement": total_engagement,
            "avg_engagement_per_comment": round(total_engagement / len(self.comments), 1),
            "sentiment_distribution": distribution,
        }
    
    def to_dict(self) -> dict:
        """Serialize to dict."""
        return {
            "video_id": self.video_id,
            "video_title": self.video_title,
            "comments": [comment.to_dict() for comment in self.comments],
            "metrics": self.aggregate_sentiment(),
        }


def ingest_youtube_comments_dry_run(video_id: str = "test-video") -> YouTubeCommentThread:
    """
    Return deterministic mock YouTube comments for testing.
    
    Args:
        video_id: Video ID (unused in dry-run, for API compatibility)
        
    Returns:
        YouTubeCommentThread with mock comments
    """
    comments = [
        YouTubeComment(
            author="GoldBull2025",
            text="Gold prices look bullish! Central bank fears are driving demand.",
            sentiment=YouTubeSentimentLabel.POSITIVE,
            likes=45,
            video_id=video_id,
        ),
        YouTubeComment(
            author="MarketSkeptic",
            text="Historical patterns suggest consolidation before major move",
            sentiment=YouTubeSentimentLabel.NEUTRAL,
            likes=12,
            video_id=video_id,
        ),
        YouTubeComment(
            author="TechTrader",
            text="Technical breakdown suggests further downside risk",
            sentiment=YouTubeSentimentLabel.NEGATIVE,
            likes=8,
            video_id=video_id,
        ),
        YouTubeComment(
            author="CentralBankWatcher",
            text="MUST WATCH: The Fed is definitely cutting rates soon",
            sentiment=YouTubeSentimentLabel.VERY_POSITIVE,
            likes=132,
            video_id=video_id,
        ),
        YouTubeComment(
            author="BearishOnAll",
            text="This is a complete scam, gold will crash 50%",
            sentiment=YouTubeSentimentLabel.VERY_NEGATIVE,
            likes=3,
            video_id=video_id,
        ),
    ]
    
    return YouTubeCommentThread(
        video_id=video_id,
        video_title="Gold Market Analysis 2026",
        comments=comments,
    )


def ingest_youtube_comments_live(video_id: str, api_key: Optional[str] = None) -> YouTubeCommentThread:
    """
    Fetch live YouTube comments from video (stub for future implementation).
    
    Current implementation: returns error prompting for API key.
    
    Args:
        video_id: YouTube video ID
        api_key: YouTube Data API v3 key
        
    Returns:
        YouTubeCommentThread with live comments
        
    Raises:
        RuntimeError: If API key not configured or API call fails
    """
    if not api_key:
        raise RuntimeError("Live YouTube comment ingestion requires JARVIS_YOUTUBE_API_KEY")
    
    # TODO: Integrate with YouTube Data API v3
    # Would call: youtube = googleapiclient.discovery.build('youtube', 'v3', developerKey=api_key)
    # Then: youtube.commentThreads().list(videoId=video_id, textFormat='plainText')
    raise RuntimeError("Live YouTube comment ingestion not yet implemented")


def get_youtube_sentiment(
    video_id: str = "dQw4w9WgXcQ",
    mode: str = "dry_run",
    api_key: Optional[str] = None,
) -> dict:
    """
    Unified YouTube sentiment getter supporting dry_run and live modes.
    
    Args:
        video_id: YouTube video ID to analyze
        mode: "dry_run" or "live"
        api_key: API key for live mode
        
    Returns:
        Dict with thread data and aggregate sentiment metrics
        
    Raises:
        RuntimeError: If live mode requested but API not available
        ValueError: If invalid mode
    """
    if mode == "dry_run":
        thread = ingest_youtube_comments_dry_run(video_id)
    elif mode == "live":
        thread = ingest_youtube_comments_live(video_id, api_key=api_key)
    else:
        raise ValueError(f"Unknown YouTube sentiment mode: {mode}")
    
    result = thread.to_dict()
    result["ok"] = True
    result["mode"] = mode
    result["timestamp"] = datetime.now(timezone.utc).isoformat()
    return result
