"""Decay middleware — gradually reduces retry aggressiveness after sustained failures.

If a command fails repeatedly over a long run, the decay factor multiplies
the base delay to back off more aggressively without changing BackoffConfig.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class DecayConfig:
    enabled: bool = False
    # Number of consecutive failures before decay kicks in
    threshold: int = 3
    # Multiplier applied per failure beyond threshold (e.g. 1.2 = 20% extra each time)
    factor: float = 1.2
    # Maximum multiplier cap so delays don't explode
    max_multiplier: float = 8.0

    def __post_init__(self) -> None:
        if self.threshold < 1:
            raise ValueError("decay threshold must be >= 1")
        if self.factor < 1.0:
            raise ValueError("decay factor must be >= 1.0")
        if self.max_multiplier < 1.0:
            raise ValueError("decay max_multiplier must be >= 1.0")

    @classmethod
    def from_dict(cls, data: dict) -> "DecayConfig":
        if not isinstance(data, dict):
            raise TypeError("decay config must be a mapping")
        enabled = bool(data.get("enabled", False))
        threshold = int(data.get("threshold", 3))
        factor = float(data.get("factor", 1.2))
        max_multiplier = float(data.get("max_multiplier", 8.0))
        # Auto-enable if non-default factor supplied
        if "factor" in data and not data.get("enabled", False):
            enabled = True
        return cls(
            enabled=enabled,
            threshold=threshold,
            factor=factor,
            max_multiplier=max_multiplier,
        )


@dataclass
class DecayTracker:
    config: DecayConfig
    _consecutive_failures: int = field(default=0, init=False)

    def record_failure(self) -> None:
        self._consecutive_failures += 1

    def record_success(self) -> None:
        self._consecutive_failures = 0

    def current_multiplier(self) -> float:
        """Return the delay multiplier to apply given current failure streak."""
        cfg = self.config
        if not cfg.enabled:
            return 1.0
        excess = max(0, self._consecutive_failures - cfg.threshold)
        if excess == 0:
            return 1.0
        raw = math.pow(cfg.factor, excess)
        return min(raw, cfg.max_multiplier)

    def apply(self, delay: float) -> float:
        """Return delay scaled by the current decay multiplier."""
        return delay * self.current_multiplier()
