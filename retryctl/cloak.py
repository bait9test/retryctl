"""Cloak — probabilistically mask attempts from metrics/alerts without skipping them."""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class CloakConfig:
    enabled: bool = False
    mask_rate: float = 0.0          # 0.0–1.0 probability an attempt is cloaked
    seed: Optional[int] = None      # reproducible behaviour in tests
    tag: str = "cloaked"            # label attached to cloaked attempts

    def __post_init__(self) -> None:
        if not 0.0 <= self.mask_rate <= 1.0:
            raise ValueError(f"mask_rate must be in [0, 1], got {self.mask_rate}")

    @staticmethod
    def from_dict(raw: object) -> "CloakConfig":
        if not isinstance(raw, dict):
            raise TypeError(f"[cloak] config must be a dict, got {type(raw).__name__}")
        mask_rate = float(raw.get("mask_rate", 0.0))
        enabled = bool(raw.get("enabled", mask_rate > 0.0))
        seed = raw.get("seed")
        tag = str(raw.get("tag", "cloaked"))
        return CloakConfig(enabled=enabled, mask_rate=mask_rate,
                           seed=seed, tag=tag)


class CloakedAttempt(Exception):
    """Raised (internally) when an attempt is marked as cloaked."""
    def __init__(self, attempt: int, tag: str) -> None:
        super().__init__(f"attempt {attempt} cloaked [{tag}]")
        self.attempt = attempt
        self.tag = tag


@dataclass
class CloakTracker:
    config: CloakConfig
    _rng: random.Random = field(init=False, repr=False)
    _cloaked: list[int] = field(default_factory=list, init=False)

    def __post_init__(self) -> None:
        self._rng = random.Random(self.config.seed)

    def is_cloaked(self, attempt: int) -> bool:
        """Return True and record the attempt if it should be cloaked."""
        if not self.config.enabled:
            return False
        if self._rng.random() < self.config.mask_rate:
            self._cloaked.append(attempt)
            return True
        return False

    @property
    def cloaked_attempts(self) -> list[int]:
        return list(self._cloaked)

    def summary(self) -> str:
        n = len(self._cloaked)
        return f"cloak: {n} attempt(s) masked as '{self.config.tag}'"
