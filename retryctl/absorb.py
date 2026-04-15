"""absorb.py — suppress transient errors below a consecutive-failure threshold.

If the number of consecutive failures stays below `threshold`, the run is
treated as succeeded from the caller's perspective.  Once the threshold is
reached the failures are "released" and propagate normally.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict


@dataclass
class AbsorbConfig:
    enabled: bool = False
    threshold: int = 3  # consecutive failures before releasing

    @staticmethod
    def from_dict(raw: dict) -> "AbsorbConfig":
        if not isinstance(raw, dict):
            raise TypeError(f"absorb config must be a dict, got {type(raw).__name__}")
        enabled = raw.get("enabled", False)
        threshold = int(raw.get("threshold", 3))
        if threshold < 1:
            raise ValueError("absorb threshold must be >= 1")
        auto_enable = "threshold" in raw
        return AbsorbConfig(
            enabled=bool(enabled) or auto_enable,
            threshold=threshold,
        )


@dataclass
class AbsorbState:
    consecutive_failures: int = 0

    def record_failure(self) -> None:
        self.consecutive_failures += 1

    def record_success(self) -> None:
        self.consecutive_failures = 0

    def is_absorbed(self, threshold: int) -> bool:
        """Return True while failures are still below the threshold."""
        return self.consecutive_failures < threshold


# Module-level registry so middleware can share state across calls.
_registry: Dict[str, AbsorbState] = {}


def _get_state(key: str) -> AbsorbState:
    if key not in _registry:
        _registry[key] = AbsorbState()
    return _registry[key]


def check_absorbed(cfg: AbsorbConfig, key: str, failed: bool) -> bool:
    """Update state and return True if the failure should be absorbed."""
    if not cfg.enabled:
        return False
    state = _get_state(key)
    if failed:
        state.record_failure()
        return state.is_absorbed(cfg.threshold)
    else:
        state.record_success()
        return False


def reset_absorb_state(key: str) -> None:
    """Clear persisted state for a key (useful in tests)."""
    _registry.pop(key, None)
