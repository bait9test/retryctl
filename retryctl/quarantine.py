"""Quarantine — temporarily block a command key after repeated failures.

Once a key accumulates `threshold` failures within `window_seconds`,
it is quarantined for `duration_seconds` and all attempts are blocked.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class QuarantineConfig:
    enabled: bool = False
    threshold: int = 5
    window_seconds: float = 60.0
    duration_seconds: float = 300.0
    key: str = "default"

    @staticmethod
    def from_dict(data: dict) -> "QuarantineConfig":
        if not isinstance(data, dict):
            raise TypeError("quarantine config must be a mapping")
        threshold = int(data.get("threshold", 5))
        if threshold < 1:
            raise ValueError("threshold must be >= 1")
        window = float(data.get("window_seconds", 60.0))
        if window <= 0:
            raise ValueError("window_seconds must be positive")
        duration = float(data.get("duration_seconds", 300.0))
        if duration <= 0:
            raise ValueError("duration_seconds must be positive")
        key = str(data.get("key", "default")) or "default"
        enabled = bool(data.get("enabled", bool(key and key != "default")))
        return QuarantineConfig(
            enabled=enabled,
            threshold=threshold,
            window_seconds=window,
            duration_seconds=duration,
            key=key,
        )


class QuarantineBlocked(Exception):
    def __init__(self, key: str, release_at: float) -> None:
        self.key = key
        self.release_at = release_at
        remaining = max(0.0, release_at - time.monotonic())
        super().__init__(
            f"key '{key}' is quarantined for {remaining:.1f}s more"
        )


@dataclass
class _QuarantineState:
    failure_times: List[float] = field(default_factory=list)
    quarantined_until: float = 0.0


_registry: Dict[str, _QuarantineState] = {}


def _state_for(key: str) -> _QuarantineState:
    if key not in _registry:
        _registry[key] = _QuarantineState()
    return _registry[key]


def check_quarantine(cfg: QuarantineConfig) -> None:
    """Raise QuarantineBlocked if the key is currently quarantined."""
    if not cfg.enabled:
        return
    state = _state_for(cfg.key)
    now = time.monotonic()
    if now < state.quarantined_until:
        raise QuarantineBlocked(cfg.key, state.quarantined_until)


def record_failure(cfg: QuarantineConfig) -> None:
    """Record a failure; quarantine the key if threshold is reached."""
    if not cfg.enabled:
        return
    state = _state_for(cfg.key)
    now = time.monotonic()
    state.failure_times.append(now)
    # evict failures outside the window
    cutoff = now - cfg.window_seconds
    state.failure_times = [t for t in state.failure_times if t >= cutoff]
    if len(state.failure_times) >= cfg.threshold:
        state.quarantined_until = now + cfg.duration_seconds
        state.failure_times.clear()


def record_success(cfg: QuarantineConfig) -> None:
    """Clear failure history on success."""
    if not cfg.enabled:
        return
    state = _state_for(cfg.key)
    state.failure_times.clear()
