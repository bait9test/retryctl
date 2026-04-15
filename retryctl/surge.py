"""surge.py — detect and respond to sudden spikes in failure rate."""
from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from typing import Deque


@dataclass
class SurgeConfig:
    enabled: bool = False
    window_seconds: float = 60.0
    threshold: int = 5          # failures within the window to trigger
    cooldown_seconds: float = 30.0  # how long to pause once surge detected

    @classmethod
    def from_dict(cls, raw: dict) -> "SurgeConfig":
        if not isinstance(raw, dict):
            raise TypeError(f"SurgeConfig expects a dict, got {type(raw).__name__}")
        window = float(raw.get("window_seconds", 60.0))
        threshold = int(raw.get("threshold", 5))
        cooldown = float(raw.get("cooldown_seconds", 30.0))
        if window <= 0:
            raise ValueError("window_seconds must be positive")
        if threshold < 1:
            raise ValueError("threshold must be at least 1")
        if cooldown < 0:
            raise ValueError("cooldown_seconds must be non-negative")
        enabled = bool(raw.get("enabled", threshold > 0))
        return cls(
            enabled=enabled,
            window_seconds=window,
            threshold=threshold,
            cooldown_seconds=cooldown,
        )


class SurgeDetected(Exception):
    def __init__(self, cooldown: float) -> None:
        self.cooldown = cooldown
        super().__init__(
            f"Surge detected — backing off for {cooldown:.1f}s"
        )


@dataclass
class SurgeTracker:
    config: SurgeConfig
    _timestamps: Deque[float] = field(default_factory=deque, init=False)

    def _evict(self, now: float) -> None:
        cutoff = now - self.config.window_seconds
        while self._timestamps and self._timestamps[0] < cutoff:
            self._timestamps.popleft()

    def record_failure(self, now: float | None = None) -> None:
        """Record a failure; raises SurgeDetected if threshold is breached."""
        if not self.config.enabled:
            return
        ts = now if now is not None else time.monotonic()
        self._evict(ts)
        self._timestamps.append(ts)
        if len(self._timestamps) >= self.config.threshold:
            self._timestamps.clear()
            raise SurgeDetected(self.config.cooldown_seconds)

    def record_success(self) -> None:
        """A success resets the rolling window."""
        if self.config.enabled:
            self._timestamps.clear()

    @property
    def failure_count(self) -> int:
        self._evict(time.monotonic())
        return len(self._timestamps)
