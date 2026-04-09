"""Rate limiting support for retryctl — prevents hammering a failing service."""

from __future__ import annotations

import time
import logging
from dataclasses import dataclass, field
from collections import deque
from typing import Deque

logger = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting retry attempts."""

    max_attempts_per_window: int = 0  # 0 means disabled
    window_seconds: float = 60.0

    @property
    def enabled(self) -> bool:
        return self.max_attempts_per_window > 0


@dataclass
class RateLimiter:
    """Sliding-window rate limiter that tracks attempt timestamps."""

    config: RateLimitConfig
    _timestamps: Deque[float] = field(default_factory=deque, init=False)

    def _evict_expired(self, now: float) -> None:
        cutoff = now - self.config.window_seconds
        while self._timestamps and self._timestamps[0] < cutoff:
            self._timestamps.popleft()

    def is_allowed(self, now: float | None = None) -> bool:
        """Return True if a new attempt is allowed under the current rate limit."""
        if not self.config.enabled:
            return True
        now = now if now is not None else time.monotonic()
        self._evict_expired(now)
        return len(self._timestamps) < self.config.max_attempts_per_window

    def record(self, now: float | None = None) -> None:
        """Record that an attempt occurred at *now*."""
        now = now if now is not None else time.monotonic()
        self._timestamps.append(now)

    def wait_until_allowed(self) -> None:
        """Block until a new attempt is permitted, then record it."""
        if not self.config.enabled:
            return
        while True:
            now = time.monotonic()
            self._evict_expired(now)
            if len(self._timestamps) < self.config.max_attempts_per_window:
                self.record(now)
                return
            oldest = self._timestamps[0]
            sleep_for = oldest + self.config.window_seconds - now
            logger.debug(
                "Rate limit reached (%d/%d in %.1fs window); sleeping %.2fs",
                len(self._timestamps),
                self.config.max_attempts_per_window,
                self.config.window_seconds,
                sleep_for,
            )
            time.sleep(max(sleep_for, 0.0))
