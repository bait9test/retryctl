"""Retry budget: cap the total number of retries within a rolling time window."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import List


@dataclass
class BudgetConfig:
    enabled: bool = False
    max_retries: int = 0          # total retry attempts allowed in the window
    window_seconds: float = 60.0  # rolling window size in seconds
    key: str = "default"

    @staticmethod
    def from_dict(data: dict) -> "BudgetConfig":
        max_r = int(data.get("max_retries", 0))
        window = float(data.get("window_seconds", 60.0))
        if window <= 0:
            raise ValueError("budget window_seconds must be positive")
        return BudgetConfig(
            enabled=bool(data.get("enabled", max_r > 0)),
            max_retries=max_r,
            window_seconds=window,
            key=str(data.get("key", "default")),
        )


class BudgetExceeded(Exception):
    """Raised when the retry budget for a key is exhausted."""

    def __init__(self, key: str, used: int, limit: int, window: float) -> None:
        self.key = key
        self.used = used
        self.limit = limit
        self.window = window
        super().__init__(
            f"Retry budget exceeded for '{key}': "
            f"{used}/{limit} retries used in the last {window}s window"
        )


@dataclass
class BudgetTracker:
    config: BudgetConfig
    _timestamps: List[float] = field(default_factory=list)

    def _evict_expired(self, now: float) -> None:
        cutoff = now - self.config.window_seconds
        self._timestamps = [t for t in self._timestamps if t >= cutoff]

    def is_allowed(self) -> bool:
        if not self.config.enabled:
            return True
        now = time.monotonic()
        self._evict_expired(now)
        return len(self._timestamps) < self.config.max_retries

    def record_retry(self) -> None:
        if self.config.enabled:
            self._timestamps.append(time.monotonic())

    def check_or_raise(self) -> None:
        if not self.config.enabled:
            return
        now = time.monotonic()
        self._evict_expired(now)
        used = len(self._timestamps)
        if used >= self.config.max_retries:
            raise BudgetExceeded(
                self.config.key, used, self.config.max_retries, self.config.window_seconds
            )

    def remaining(self) -> int:
        if not self.config.enabled:
            return -1
        now = time.monotonic()
        self._evict_expired(now)
        return max(0, self.config.max_retries - len(self._timestamps))
