"""Sliding-window failure rate tracker for retryctl.

Tracks the ratio of failed attempts within a rolling time window and
raises WindowBreached when the failure rate exceeds a configured threshold.
"""
from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from typing import Deque


@dataclass
class WindowConfig:
    enabled: bool = False
    window_seconds: float = 60.0
    min_attempts: int = 3
    max_failure_rate: float = 0.5  # 0.0–1.0

    @classmethod
    def from_dict(cls, raw: dict) -> "WindowConfig":
        if not isinstance(raw, dict):
            raise TypeError(f"WindowConfig expects a dict, got {type(raw).__name__}")
        window_seconds = float(raw.get("window_seconds", 60.0))
        if window_seconds <= 0:
            raise ValueError("window_seconds must be positive")
        min_attempts = int(raw.get("min_attempts", 3))
        if min_attempts < 1:
            raise ValueError("min_attempts must be >= 1")
        max_failure_rate = float(raw.get("max_failure_rate", 0.5))
        if not (0.0 < max_failure_rate <= 1.0):
            raise ValueError("max_failure_rate must be in (0.0, 1.0]")
        enabled = bool(raw.get("enabled", True))
        return cls(
            enabled=enabled,
            window_seconds=window_seconds,
            min_attempts=min_attempts,
            max_failure_rate=max_failure_rate,
        )


class WindowBreached(Exception):
    def __init__(self, rate: float, threshold: float) -> None:
        self.rate = rate
        self.threshold = threshold

    def __str__(self) -> str:
        return (
            f"failure rate {self.rate:.0%} exceeds threshold {self.threshold:.0%}"
        )


@dataclass
class WindowTracker:
    config: WindowConfig
    _timestamps: Deque[float] = field(default_factory=deque, init=False)
    _failures: Deque[bool] = field(default_factory=deque, init=False)

    def _evict(self, now: float) -> None:
        cutoff = now - self.config.window_seconds
        while self._timestamps and self._timestamps[0] < cutoff:
            self._timestamps.popleft()
            self._failures.popleft()

    def record(self, *, failed: bool, now: float | None = None) -> None:
        if not self.config.enabled:
            return
        ts = now if now is not None else time.monotonic()
        self._evict(ts)
        self._timestamps.append(ts)
        self._failures.append(failed)

    def check(self, now: float | None = None) -> None:
        """Raise WindowBreached if the failure rate is too high."""
        if not self.config.enabled:
            return
        ts = now if now is not None else time.monotonic()
        self._evict(ts)
        total = len(self._failures)
        if total < self.config.min_attempts:
            return
        rate = sum(self._failures) / total
        if rate > self.config.max_failure_rate:
            raise WindowBreached(rate, self.config.max_failure_rate)

    @property
    def failure_rate(self) -> float | None:
        if not self._failures:
            return None
        return sum(self._failures) / len(self._failures)
