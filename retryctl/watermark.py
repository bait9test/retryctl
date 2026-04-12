"""High-watermark tracker: raise an alert when consecutive failures exceed a threshold."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

log = logging.getLogger(__name__)


@dataclass
class WatermarkConfig:
    enabled: bool = False
    threshold: int = 3          # consecutive failures before watermark is breached
    reset_on_success: bool = True

    @staticmethod
    def from_dict(data: dict) -> "WatermarkConfig":
        if not isinstance(data, dict):
            raise TypeError(f"WatermarkConfig expects a dict, got {type(data).__name__}")
        threshold = int(data.get("threshold", 3))
        if threshold < 1:
            raise ValueError("watermark threshold must be >= 1")
        enabled = bool(data.get("enabled", False))
        reset_on_success = bool(data.get("reset_on_success", True))
        return WatermarkConfig(enabled=enabled, threshold=threshold, reset_on_success=reset_on_success)


@dataclass
class WatermarkBreached(Exception):
    consecutive: int
    threshold: int

    def __str__(self) -> str:
        return (
            f"Watermark breached: {self.consecutive} consecutive failures "
            f"(threshold={self.threshold})"
        )


@dataclass
class WatermarkTracker:
    config: WatermarkConfig
    _consecutive: int = field(default=0, init=False)

    @property
    def consecutive(self) -> int:
        return self._consecutive

    def record_failure(self) -> None:
        """Increment consecutive failure count and raise if threshold is breached."""
        if not self.config.enabled:
            return
        self._consecutive += 1
        log.debug("watermark: consecutive failures=%d threshold=%d", self._consecutive, self.config.threshold)
        if self._consecutive >= self.config.threshold:
            raise WatermarkBreached(consecutive=self._consecutive, threshold=self.config.threshold)

    def record_success(self) -> None:
        """Reset consecutive count on success if configured to do so."""
        if self.config.reset_on_success:
            self._consecutive = 0

    def reset(self) -> None:
        self._consecutive = 0
