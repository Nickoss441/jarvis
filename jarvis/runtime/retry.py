"""Retry policy for transient tool failures.

Only ``tool-failure`` errors (unexpected handler exceptions) are retried.
``policy-denied``, ``tool-not-found``, and ``tool-bad-args`` are
deterministic and must not be retried.

Usage::

    policy = RetryPolicy(max_attempts=3)
    for attempt in range(1, policy.max_attempts + 1):
        try:
            result = handler(**args)
            break
        except Exception:
            if not policy.should_retry(attempt):
                raise
            # loop continues
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RetryPolicy:
    """Value object controlling retry behaviour for transient tool failures.

    Parameters
    ----------
    max_attempts:
        Total number of attempts (including the first).  Must be >= 1.
        Defaults to 2 (one retry on first failure).
    """

    max_attempts: int = 2

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError(f"max_attempts must be >= 1, got {self.max_attempts}")

    def should_retry(self, attempt: int) -> bool:
        """Return True if *attempt* was not the last allowed attempt.

        Parameters
        ----------
        attempt:
            The 1-based attempt number that just completed.
        """
        return attempt < self.max_attempts
