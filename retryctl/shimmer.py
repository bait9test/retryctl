"""shimmer: probabilistic attempt skipping based on a configured skip rate.

When enabled, each attempt has a chance of being skipped (no-op) instead of
running the actual command. Useful for canary-style load shedding in tests.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ShimmerConfig:
    enabled: bool = False
    skip_rate: float = 0.0  # 0.0 to 1.0
    seed: int | None = None

    def __post_init__(self) -> None:
        if not (0.0 <= self.skip_rate <= 1.0):
            raise ValueError(f"skip_rate must be between 0.0 and 1.0, got {self.skip_rate}")

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "ShimmerConfig":
        if not isinstance(raw, dict):
            raise TypeError(f"shimmer config must be a dict, got {type(raw).__name__}")
        skip_rate = float(raw.get("skip_rate", 0.0))
        enabled = bool(raw.get("enabled", skip_rate > 0.0))
        seed = raw.get("seed")
        if seed is not None:
            seed = int(seed)
        return cls(enabled=enabled, skip_rate=skip_rate, seed=seed)


class ShimmerSkipped(Exception):
    """Raised when an attempt is skipped by the shimmer."""

    def __init__(self, attempt: int, skip_rate: float) -> None:
        self.attempt = attempt
        self.skip_rate = skip_rate
        super().__init__(f"attempt {attempt} skipped by shimmer (rate={skip_rate:.2f})")


class ShimmerTracker:
    def __init__(self, cfg: ShimmerConfig) -> None:
        self._cfg = cfg
        self._rng = random.Random(cfg.seed)
        self.skipped: int = 0
        self.allowed: int = 0

    def should_skip(self, attempt: int) -> bool:
        if not self._cfg.enabled or self._cfg.skip_rate <= 0.0:
            self.allowed += 1
            return False
        if self._rng.random() < self._cfg.skip_rate:
            self.skipped += 1
            return True
        self.allowed += 1
        return False

    def check(self, attempt: int) -> None:
        """Raise ShimmerSkipped if this attempt should be skipped."""
        if self.should_skip(attempt):
            raise ShimmerSkipped(attempt, self._cfg.skip_rate)
