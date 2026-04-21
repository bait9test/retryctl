"""veil.py — Probabilistic attempt suppression based on a configurable drop rate.

When enabled, each attempt has a `drop_rate` chance of being silently skipped.
Useful for load-shedding in high-frequency retry loops.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any


@dataclass
class VeilConfig:
    enabled: bool = False
    drop_rate: float = 0.0  # 0.0 – 1.0
    seed: int | None = None

    def __post_init__(self) -> None:
        if not (0.0 <= self.drop_rate <= 1.0):
            raise ValueError(f"drop_rate must be between 0.0 and 1.0, got {self.drop_rate}")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "VeilConfig":
        if not isinstance(data, dict):
            raise TypeError(f"VeilConfig expects a dict, got {type(data).__name__}")
        rate = float(data.get("drop_rate", 0.0))
        enabled = bool(data.get("enabled", rate > 0.0))
        seed = data.get("seed")
        return cls(enabled=enabled, drop_rate=rate, seed=seed)


class VeiledAttempt(Exception):
    """Raised when an attempt is dropped by the veil."""

    def __init__(self, attempt: int, drop_rate: float) -> None:
        self.attempt = attempt
        self.drop_rate = drop_rate
        super().__init__(f"attempt {attempt} veiled (drop_rate={drop_rate:.2%})")


@dataclass
class VeilTracker:
    config: VeilConfig
    _rng: random.Random = field(init=False)

    def __post_init__(self) -> None:
        self._rng = random.Random(self.config.seed)

    def should_drop(self) -> bool:
        if not self.config.enabled or self.config.drop_rate <= 0.0:
            return False
        return self._rng.random() < self.config.drop_rate

    def check(self, attempt: int) -> None:
        """Raise VeiledAttempt if this attempt should be dropped."""
        if self.should_drop():
            raise VeiledAttempt(attempt, self.config.drop_rate)
