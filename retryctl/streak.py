"""streak.py — track consecutive success/failure runs."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class StreakConfig:
    enabled: bool = False
    warn_on_failure_streak: int = 0   # emit warning after N consecutive failures
    reset_on_success: bool = True

    @classmethod
    def from_dict(cls, raw: dict) -> "StreakConfig":
        if not isinstance(raw, dict):
            raise TypeError(f"streak config must be a dict, got {type(raw).__name__}")
        warn = int(raw.get("warn_on_failure_streak", 0))
        if warn < 0:
            raise ValueError("warn_on_failure_streak must be >= 0")
        enabled = bool(raw.get("enabled", warn > 0))
        reset = bool(raw.get("reset_on_success", True))
        return cls(enabled=enabled, warn_on_failure_streak=warn, reset_on_success=reset)


@dataclass
class StreakState:
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    last_updated: float = field(default_factory=time.monotonic)

    def record_failure(self) -> None:
        self.consecutive_failures += 1
        self.consecutive_successes = 0
        self.last_updated = time.monotonic()

    def record_success(self) -> None:
        self.consecutive_successes += 1
        self.consecutive_failures = 0
        self.last_updated = time.monotonic()

    def to_dict(self) -> dict:
        return {
            "consecutive_failures": self.consecutive_failures,
            "consecutive_successes": self.consecutive_successes,
            "last_updated": self.last_updated,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "StreakState":
        obj = cls()
        obj.consecutive_failures = int(d.get("consecutive_failures", 0))
        obj.consecutive_successes = int(d.get("consecutive_successes", 0))
        obj.last_updated = float(d.get("last_updated", time.monotonic()))
        return obj


def check_streak_warning(cfg: StreakConfig, state: StreakState) -> Optional[str]:
    """Return a warning message if the failure streak threshold is breached, else None."""
    if not cfg.enabled:
        return None
    if cfg.warn_on_failure_streak > 0 and state.consecutive_failures >= cfg.warn_on_failure_streak:
        return (
            f"Failure streak warning: {state.consecutive_failures} consecutive failures "
            f"(threshold={cfg.warn_on_failure_streak})"
        )
    return None
