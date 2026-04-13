"""pressure.py – tracks consecutive failure pressure and emits warnings.

When the number of consecutive failures exceeds a configurable threshold the
tracker raises PressureWarning so callers can take defensive action (e.g.
slowing down, alerting, or aborting).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

log = logging.getLogger(__name__)


@dataclass
class PressureConfig:
    enabled: bool = False
    threshold: int = 5          # consecutive failures before warning
    max_pressure: int = 10      # hard ceiling; raises PressureWarning
    reset_on_success: bool = True

    @classmethod
    def from_dict(cls, raw: dict) -> "PressureConfig":
        if not isinstance(raw, dict):
            raise TypeError(f"PressureConfig expects a dict, got {type(raw).__name__}")
        threshold = int(raw.get("threshold", 5))
        max_pressure = int(raw.get("max_pressure", 10))
        if threshold < 1:
            raise ValueError("pressure.threshold must be >= 1")
        if max_pressure < threshold:
            raise ValueError("pressure.max_pressure must be >= threshold")
        enabled = bool(raw.get("enabled", bool(raw.get("threshold"))))
        return cls(
            enabled=enabled,
            threshold=threshold,
            max_pressure=max_pressure,
            reset_on_success=bool(raw.get("reset_on_success", True)),
        )


class PressureWarning(Exception):
    """Raised when consecutive failure pressure exceeds max_pressure."""

    def __init__(self, count: int, max_pressure: int) -> None:
        self.count = count
        self.max_pressure = max_pressure
        super().__init__(
            f"pressure ceiling reached: {count} consecutive failures "
            f"(max={max_pressure})"
        )


@dataclass
class PressureTracker:
    config: PressureConfig
    _consecutive: int = field(default=0, init=False)

    def record_failure(self) -> None:
        """Call after each failed attempt."""
        if not self.config.enabled:
            return
        self._consecutive += 1
        if self._consecutive >= self.config.threshold:
            log.warning(
                "pressure warning: %d consecutive failures (threshold=%d)",
                self._consecutive,
                self.config.threshold,
            )
        if self._consecutive >= self.config.max_pressure:
            raise PressureWarning(self._consecutive, self.config.max_pressure)

    def record_success(self) -> None:
        """Call after a successful attempt."""
        if not self.config.enabled:
            return
        if self.config.reset_on_success:
            self._consecutive = 0

    @property
    def consecutive(self) -> int:
        return self._consecutive
