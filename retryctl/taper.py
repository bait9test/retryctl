"""taper.py — gradually reduce retry aggressiveness after sustained failures.

A TaperTracker monitors consecutive failures and, once a threshold is
reached, multiplies the computed backoff delay by an escalating factor.
This slows down retry storms when a dependency is clearly unhealthy,
without permanently blocking retries the way a circuit-breaker does.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

log = logging.getLogger(__name__)


@dataclass
class TaperConfig:
    """Configuration for the taper middleware."""

    enabled: bool = False
    # Number of consecutive failures before tapering begins.
    threshold: int = 3
    # Multiply the backoff delay by this factor for each failure beyond the
    # threshold.  Must be >= 1.0.
    factor: float = 1.5
    # Hard ceiling on the taper multiplier so delays don't grow unboundedly.
    max_multiplier: float = 10.0

    def __post_init__(self) -> None:
        if self.threshold < 1:
            raise ValueError("taper threshold must be >= 1")
        if self.factor < 1.0:
            raise ValueError("taper factor must be >= 1.0")
        if self.max_multiplier < 1.0:
            raise ValueError("taper max_multiplier must be >= 1.0")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TaperConfig":
        """Construct from a raw config mapping (e.g. parsed TOML section)."""
        if not isinstance(data, dict):
            raise TypeError(f"taper config must be a dict, got {type(data).__name__}")

        threshold = int(data.get("threshold", 3))
        factor = float(data.get("factor", 1.5))
        max_multiplier = float(data.get("max_multiplier", 10.0))

        # Auto-enable when a meaningful factor is supplied.
        explicit_enabled = data.get("enabled")
        if explicit_enabled is not None:
            enabled = bool(explicit_enabled)
        else:
            enabled = factor > 1.0

        return cls(
            enabled=enabled,
            threshold=threshold,
            factor=factor,
            max_multiplier=max_multiplier,
        )


@dataclass
class TaperState:
    """Mutable runtime state tracked per-command-key."""

    consecutive_failures: int = 0

    def record_failure(self) -> None:
        self.consecutive_failures += 1

    def record_success(self) -> None:
        self.consecutive_failures = 0

    def multiplier(self, cfg: TaperConfig) -> float:
        """Return the current delay multiplier based on failure count."""
        if not cfg.enabled or self.consecutive_failures <= cfg.threshold:
            return 1.0
        excess = self.consecutive_failures - cfg.threshold
        raw = cfg.factor ** excess
        return min(raw, cfg.max_multiplier)


def apply_taper(delay: float, state: TaperState, cfg: TaperConfig) -> float:
    """Return *delay* scaled by the current taper multiplier.

    If tapering is disabled or the failure count is below the threshold the
    original delay is returned unchanged.
    """
    if not cfg.enabled:
        return delay

    m = state.multiplier(cfg)
    if m > 1.0:
        scaled = delay * m
        log.debug(
            "taper: %d consecutive failures (threshold=%d) — "
            "multiplier=%.2f, delay %.3fs -> %.3fs",
            state.consecutive_failures,
            cfg.threshold,
            m,
            delay,
            scaled,
        )
        return scaled
    return delay
