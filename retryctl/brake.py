"""brake.py – gradual slow-down when consecutive failures accumulate.

When the failure streak exceeds `threshold`, each subsequent attempt
incurs an additional `step_ms` milliseconds of delay (capped at `max_ms`).
On success the extra delay is reset to zero.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

log = logging.getLogger(__name__)


@dataclass
class BrakeConfig:
    enabled: bool = False
    threshold: int = 3        # consecutive failures before braking starts
    step_ms: int = 500        # ms added per failure beyond threshold
    max_ms: int = 10_000      # ceiling on added delay

    def __post_init__(self) -> None:
        if self.threshold < 1:
            raise ValueError("brake.threshold must be >= 1")
        if self.step_ms < 0:
            raise ValueError("brake.step_ms must be >= 0")
        if self.max_ms < 0:
            raise ValueError("brake.max_ms must be >= 0")

    @classmethod
    def from_dict(cls, raw: object) -> "BrakeConfig":
        if not isinstance(raw, dict):
            raise TypeError(f"brake config must be a table, got {type(raw).__name__}")
        return cls(
            enabled=bool(raw.get("enabled", False)),
            threshold=int(raw.get("threshold", 3)),
            step_ms=int(raw.get("step_ms", 500)),
            max_ms=int(raw.get("max_ms", 10_000)),
        )


@dataclass
class BrakeState:
    _consecutive_failures: int = field(default=0, repr=False)
    _extra_ms: int = field(default=0, repr=False)

    def record_failure(self, cfg: BrakeConfig) -> int:
        """Increment failure counter; return current extra delay in ms."""
        self._consecutive_failures += 1
        if self._consecutive_failures > cfg.threshold:
            self._extra_ms = min(
                self._extra_ms + cfg.step_ms,
                cfg.max_ms,
            )
            log.debug(
                "brake: %d consecutive failures – extra delay %d ms",
                self._consecutive_failures,
                self._extra_ms,
            )
        return self._extra_ms

    def record_success(self) -> None:
        """Reset on any success."""
        if self._extra_ms:
            log.debug("brake: success – resetting extra delay (was %d ms)", self._extra_ms)
        self._consecutive_failures = 0
        self._extra_ms = 0

    @property
    def extra_ms(self) -> int:
        return self._extra_ms

    @property
    def consecutive_failures(self) -> int:
        return self._consecutive_failures
