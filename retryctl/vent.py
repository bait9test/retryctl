"""vent.py – release-valve logic: pause retries when failure rate exceeds a threshold.

If the ratio of failures in the last `window` attempts exceeds `threshold`,
a VentOpen exception is raised so the caller can skip the next retry.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Deque


@dataclass
class VentConfig:
    enabled: bool = False
    threshold: float = 0.75   # fraction of failures that triggers the vent
    window: int = 10          # number of recent attempts to consider
    cooldown_seconds: float = 30.0  # how long to hold the vent open

    @staticmethod
    def from_dict(data: dict) -> "VentConfig":
        if not isinstance(data, dict):
            raise TypeError(f"VentConfig expects a dict, got {type(data).__name__}")
        threshold = float(data.get("threshold", 0.75))
        window = int(data.get("window", 10))
        cooldown = float(data.get("cooldown_seconds", 30.0))
        if not (0.0 < threshold <= 1.0):
            raise ValueError(f"threshold must be in (0, 1], got {threshold}")
        if window < 1:
            raise ValueError(f"window must be >= 1, got {window}")
        if cooldown < 0:
            raise ValueError(f"cooldown_seconds must be >= 0, got {cooldown}")
        enabled = bool(data.get("enabled", bool(data.get("threshold"))))
        return VentConfig(enabled=enabled, threshold=threshold,
                          window=window, cooldown_seconds=cooldown)


class VentOpen(Exception):
    def __init__(self, rate: float, threshold: float) -> None:
        self.rate = rate
        self.threshold = threshold
        super().__init__(
            f"vent open: failure rate {rate:.0%} >= threshold {threshold:.0%}"
        )


@dataclass
class VentTracker:
    config: VentConfig
    _history: Deque[bool] = field(default_factory=deque)  # True = failure
    _open_until: float = 0.0

    def record_failure(self) -> None:
        self._push(True)

    def record_success(self) -> None:
        self._push(False)

    def _push(self, failed: bool) -> None:
        self._history.append(failed)
        if len(self._history) > self.config.window:
            self._history.popleft()

    def check(self) -> None:
        """Raise VentOpen if the vent should be open right now."""
        import time
        if not self.config.enabled:
            return
        now = time.monotonic()
        if now < self._open_until:
            total = len(self._history)
            rate = sum(self._history) / total if total else 0.0
            raise VentOpen(rate, self.config.threshold)
        if not self._history:
            return
        rate = sum(self._history) / len(self._history)
        if rate >= self.config.threshold:
            self._open_until = now + self.config.cooldown_seconds
            raise VentOpen(rate, self.config.threshold)
