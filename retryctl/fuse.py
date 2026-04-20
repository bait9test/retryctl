"""fuse.py – Fuse breaker: halt retries after a sustained failure rate threshold.

A fuse trips when the ratio of failures within a sliding window exceeds a
configured percentage.  Once tripped the run is aborted immediately rather
than attempting further retries.
"""
from __future__ import annotations

import time
from collections import declasses import dataclass, field
from typing import Deque


@dataclass
class FuseConfig:
    enabled: bool = False
    # Minimum number of attempts before the fuse can trip.
    min_attempts: int = 3
    # Failure rate (0.0–1.0) that causes the fuse to trip.
    threshold: float = 0.8
    # Sliding window in seconds; 0 means unbounded.
    window_seconds: float = 0.0

    def __post_init__(self) -> None:
        if not 0.0 < self.threshold <= 1.0:
            raise ValueError("fuse threshold must be in (0.0, 1.0]")
        if self.min_attempts < 1:
            raise ValueError("fuse min_attempts must be >= 1")
        if self.window_seconds < 0:
            raise ValueError("fuse window_seconds must be >= 0")

    @classmethod
    def from_dict(cls, data: dict) -> "FuseConfig":
        if not isinstance(data, dict):
            raise TypeError("fuse config must be a mapping")
        enabled = bool(data.get("enabled", False))
        threshold = float(data.get("threshold", 0.8))
        min_attempts = int(data.get("min_attempts", 3))
        window_seconds = float(data.get("window_seconds", 0.0))
        # Auto-enable when a meaningful threshold is provided explicitly.
        if "threshold" in data and not data.get("enabled", False) is False:
            enabled = True
        if "threshold" in data and "enabled" not in data:
            enabled = True
        return cls(
            enabled=enabled,
            min_attempts=min_attempts,
            threshold=threshold,
            window_seconds=window_seconds,
        )


class FuseTripped(Exception):
    def __init__(self, rate: float, threshold: float, attempts: int) -> None:
        self.rate = rate
        self.threshold = threshold
        self.attempts = attempts

    def __str__(self) -> str:
        return (
            f"fuse tripped: failure rate {self.rate:.0%} "
            f"exceeds threshold {self.threshold:.0%} "
            f"after {self.attempts} attempts"
        )


@dataclass
class FuseTracker:
    config: FuseConfig
    _timestamps: Deque[float] = field(default_factory=deque)
    _failures: Deque[float] = field(default_factory=deque)

    def _evict(self) -> None:
        if self.config.window_seconds <= 0:
            return
        cutoff = time.monotonic() - self.config.window_seconds
        while self._timestamps and self._timestamps[0] < cutoff:
            self._timestamps.popleft()
            self._failures.popleft()

    def record_attempt(self, failed: bool) -> None:
        now = time.monotonic()
        self._evict()
        self._timestamps.append(now)
        self._failures.append(1.0 if failed else 0.0)

    def check(self) -> None:
        """Raise FuseTripped if the failure rate exceeds the threshold."""
        if not self.config.enabled:
            return
        self._evict()
        total = len(self._failures)
        if total < self.config.min_attempts:
            return
        rate = sum(self._failures) / total
        if rate >= self.config.threshold:
            raise FuseTripped(rate=rate, threshold=self.config.threshold, attempts=total)
