"""Quorum gate — require a minimum number of consecutive successes before
considering a command "stable" and releasing any downstream hold.

Typical use-case: after a flapping service recovers you want to see it
succeed N times in a row before marking it healthy and stopping retries.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional

log = logging.getLogger(__name__)

_DEFAULT_THRESHOLD = 3
_DEFAULT_WINDOW = 300  # seconds
_LOCK_DIR = Path("/tmp/retryctl/quorum")


@dataclass
class QuorumConfig:
    """Configuration for the quorum gate."""

    enabled: bool = False
    # Number of consecutive successes required to reach quorum.
    threshold: int = _DEFAULT_THRESHOLD
    # Rolling window in seconds; successes older than this are discarded.
    window: int = _DEFAULT_WINDOW
    # Optional namespacing key; defaults to the command string.
    key: Optional[str] = None

    def __post_init__(self) -> None:
        if self.threshold < 1:
            raise ValueError("quorum threshold must be >= 1")
        if self.window <= 0:
            raise ValueError("quorum window must be > 0")

    @classmethod
    def from_dict(cls, data: dict) -> "QuorumConfig":
        if not isinstance(data, dict):
            raise TypeError(f"quorum config must be a dict, got {type(data).__name__}")
        enabled = bool(data.get("enabled", False))
        threshold = int(data.get("threshold", _DEFAULT_THRESHOLD))
        window = int(data.get("window", _DEFAULT_WINDOW))
        key = data.get("key") or None
        # Auto-enable when threshold is explicitly supplied.
        if "threshold" in data and not data.get("enabled", False):
            enabled = True
        return cls(enabled=enabled, threshold=threshold, window=window, key=key)


class QuorumNotReached(Exception):
    """Raised when quorum has not been reached yet."""

    def __init__(self, current: int, required: int) -> None:
        self.current = current
        self.required = required
        super().__init__(
            f"quorum not reached: {current}/{required} consecutive successes"
        )


@dataclass
class _QuorumState:
    success_times: list = field(default_factory=list)


# In-process registry — sufficient for single-process use; the throttle/
# concurrency modules use file locks for cross-process coordination but
# quorum is intentionally process-local (tracks a single retry loop).
_registry: Dict[str, _QuorumState] = {}


def _sanitise_key(raw: str) -> str:
    """Produce a filesystem-safe, length-limited key string."""
    safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in raw)
    return safe[:64]


def _get_state(key: str) -> _QuorumState:
    if key not in _registry:
        _registry[key] = _QuorumState()
    return _registry[key]


def _evict_old(state: _QuorumState, window: int) -> None:
    """Remove success timestamps outside the rolling window."""
    cutoff = time.monotonic() - window
    state.success_times = [t for t in state.success_times if t >= cutoff]


def record_success(cfg: QuorumConfig, key: str) -> int:
    """Record a successful attempt and return the current consecutive count."""
    if not cfg.enabled:
        return 0
    state = _get_state(key)
    _evict_old(state, cfg.window)
    state.success_times.append(time.monotonic())
    count = len(state.success_times)
    log.debug("quorum[%s]: %d/%d successes recorded", key, count, cfg.threshold)
    return count


def record_failure(cfg: QuorumConfig, key: str) -> None:
    """Reset the success streak on any failure."""
    if not cfg.enabled:
        return
    state = _get_state(key)
    if state.success_times:
        log.debug("quorum[%s]: streak reset after failure", key)
        state.success_times.clear()


def check_quorum(cfg: QuorumConfig, key: str) -> bool:
    """Return True if quorum has been reached, False otherwise.

    Does *not* raise — callers decide whether to treat a False as a
    hard gate or merely a signal.
    """
    if not cfg.enabled:
        return True
    state = _get_state(key)
    _evict_old(state, cfg.window)
    reached = len(state.success_times) >= cfg.threshold
    if reached:
        log.info("quorum[%s]: reached (%d successes)", key, len(state.success_times))
    return reached


def enforce_quorum(cfg: QuorumConfig, key: str) -> None:
    """Raise QuorumNotReached if quorum has not been reached."""
    if not cfg.enabled:
        return
    state = _get_state(key)
    _evict_old(state, cfg.window)
    current = len(state.success_times)
    if current < cfg.threshold:
        raise QuorumNotReached(current=current, required=cfg.threshold)


def reset_quorum(key: str) -> None:
    """Completely wipe quorum state for *key* (e.g. on a new run)."""
    _registry.pop(key, None)
