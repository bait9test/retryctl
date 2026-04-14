"""flux.py — tracks the rate of change (velocity) of failures over time.

If the failure rate is accelerating beyond a threshold, FluxExceeded is raised
so the caller can back off more aggressively or abort early.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class FluxConfig:
    enabled: bool = False
    window_seconds: float = 60.0
    threshold: float = 0.5   # failures-per-second that triggers the breach
    min_samples: int = 3     # need at least this many failures before checking

    @staticmethod
    def from_dict(data: dict) -> "FluxConfig":
        if not isinstance(data, dict):
            raise TypeError("flux config must be a mapping")
        raw = data.get("flux", {})
        if not isinstance(raw, dict):
            raise TypeError("[flux] section must be a mapping")

        window = float(raw.get("window_seconds", 60.0))
        if window <= 0:
            raise ValueError("flux window_seconds must be positive")

        threshold = float(raw.get("threshold", 0.5))
        if threshold <= 0:
            raise ValueError("flux threshold must be positive")

        min_samples = int(raw.get("min_samples", 3))
        if min_samples < 1:
            raise ValueError("flux min_samples must be >= 1")

        enabled = bool(raw.get("enabled", bool(raw)))
        return FluxConfig(
            enabled=enabled,
            window_seconds=window,
            threshold=threshold,
            min_samples=min_samples,
        )


class FluxExceeded(Exception):
    def __init__(self, rate: float, threshold: float) -> None:
        self.rate = rate
        self.threshold = threshold
        super().__init__(
            f"failure flux {rate:.3f}/s exceeds threshold {threshold:.3f}/s"
        )


@dataclass
class FluxTracker:
    config: FluxConfig
    _timestamps: List[float] = field(default_factory=list)

    def _evict(self, now: Optional[float] = None) -> None:
        cutoff = (now or time.monotonic()) - self.config.window_seconds
        self._timestamps = [t for t in self._timestamps if t >= cutoff]

    def record_failure(self, now: Optional[float] = None) -> None:
        ts = now or time.monotonic()
        self._evict(ts)
        self._timestamps.append(ts)

    def check(self, now: Optional[float] = None) -> None:
        """Raise FluxExceeded if the current failure rate breaches the threshold."""
        if not self.config.enabled:
            return
        ts = now or time.monotonic()
        self._evict(ts)
        if len(self._timestamps) < self.config.min_samples:
            return
        rate = len(self._timestamps) / self.config.window_seconds
        if rate > self.config.threshold:
            raise FluxExceeded(rate, self.config.threshold)

    def reset(self) -> None:
        self._timestamps.clear()
