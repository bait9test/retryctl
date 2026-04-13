"""Pacing — enforce a minimum interval between successive attempts.

If attempts are completing faster than the configured floor, the pacing
tracker inserts an additional sleep so that the *effective* inter-attempt
delay never drops below ``min_interval_s``.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PacingConfig:
    enabled: bool = False
    min_interval_s: float = 1.0

    def __post_init__(self) -> None:
        if self.min_interval_s < 0:
            raise ValueError("min_interval_s must be >= 0")

    @classmethod
    def from_dict(cls, raw: dict) -> "PacingConfig":
        if not isinstance(raw, dict):
            raise TypeError("pacing config must be a mapping")
        min_s = float(raw.get("min_interval_s", 1.0))
        enabled = bool(raw.get("enabled", min_s > 0))
        return cls(enabled=enabled, min_interval_s=min_s)


class PacingBlocked(Exception):
    """Raised (internally) when pacing would need to block longer than tolerated."""


@dataclass
class PacingTracker:
    config: PacingConfig
    _last_attempt_time: Optional[float] = field(default=None, repr=False)

    def record_attempt_start(self) -> None:
        """Call immediately before launching an attempt."""
        self._last_attempt_time = time.monotonic()

    def wait_if_needed(self) -> float:
        """Sleep until the minimum interval has elapsed; return seconds slept."""
        if not self.config.enabled or self._last_attempt_time is None:
            return 0.0
        elapsed = time.monotonic() - self._last_attempt_time
        gap = self.config.min_interval_s - elapsed
        if gap > 0:
            time.sleep(gap)
            return gap
        return 0.0

    def reset(self) -> None:
        self._last_attempt_time = None
