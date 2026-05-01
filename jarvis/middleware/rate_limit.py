"""Simple in-memory rate limiter for Jarvis middleware."""
import threading
import time
from collections import deque


class RateLimiter:
    """Sliding-window rate limiter backed by a per-key deque.

    Parameters
    ----------
    max_calls:
        Maximum number of calls allowed within *period_seconds*.
    period_seconds:
        Length of the sliding window in seconds.
    """

    def __init__(self, max_calls: int, period_seconds: float) -> None:
        self.max_calls = max_calls
        self.period_seconds = period_seconds
        self._windows: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def check(self, key: str) -> bool:
        """Return True if the request is allowed, False if rate-limited.

        Calling this method also *records* the current call, so each
        invocation counts against the limit.
        """
        now = time.monotonic()
        cutoff = now - self.period_seconds

        with self._lock:
            if key not in self._windows:
                self._windows[key] = deque()

            window = self._windows[key]

            while window and window[0] <= cutoff:
                window.popleft()

            if len(window) >= self.max_calls:
                return False

            window.append(now)
            return True


# Shared default limiters — import these instead of constructing new ones.
DEFAULT_LIMITER = RateLimiter(60, 60)   # 60 requests per minute
HEAVY_LIMITER = RateLimiter(10, 60)    # 10 requests per minute (expensive ops)
