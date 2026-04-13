"""Tide: adaptive delay scaling based on consecutive failure streaks.

When failures accumulate beyond a threshold the delay multiplier rises;
once a success is recorded it resets back to 1.0.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TideConfig:
    enabled: bool = False
    threshold: int = 3        # failures before tide kicks in
    multiplier: float = 2.0   # factor applied to base delay each tide step
    max_multiplier: float = 16.0

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "TideConfig":
        if not isinstance(raw, dict):
            raise TypeError(f"TideConfig expects a dict, got {type(raw).__name__}")
        threshold = int(raw.get("threshold", 3))
        if threshold < 1:
            raise ValueError("tide.threshold must be >= 1")
        multiplier = float(raw.get("multiplier", 2.0))
        if multiplier < 1.0:
            raise ValueError("tide.multiplier must be >= 1.0")
        max_multiplier = float(raw.get("max_multiplier", 16.0))
        if max_multiplier < multiplier:
            raise ValueError("tide.max_multiplier must be >= multiplier")
        enabled = bool(raw.get("enabled", bool(raw)))
        return cls(
            enabled=enabled,
            threshold=threshold,
            multiplier=multiplier,
            max_multiplier=max_multiplier,
        )


@dataclass
class TideState:
    _failures: int = field(default=0, repr=False)
    _current_multiplier: float = field(default=1.0, repr=False)

    def record_failure(self, cfg: TideConfig) -> float:
        """Increment failure count and return the current multiplier."""
        self._failures += 1
        if self._failures >= cfg.threshold:
            steps = self._failures - cfg.threshold + 1
            self._current_multiplier = min(
                cfg.multiplier ** steps, cfg.max_multiplier
            )
        return self._current_multiplier

    def record_success(self) -> None:
        self._failures = 0
        self._current_multiplier = 1.0

    @property
    def current_multiplier(self) -> float:
        return self._current_multiplier

    @property
    def consecutive_failures(self) -> int:
        return self._failures


def apply_tide(base_delay: float, state: TideState, cfg: TideConfig) -> float:
    """Return base_delay scaled by the tide multiplier (no-op when disabled)."""
    if not cfg.enabled:
        return base_delay
    return base_delay * state.current_multiplier
