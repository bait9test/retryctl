"""High-level helper: wrap a callable with throttle logic.

Used by runner.py to optionally gate each retry attempt behind
a per-command file lock so parallel retryctl invocations serialise.
"""

from __future__ import annotations

import logging
from typing import Callable, Optional, TypeVar

from retryctl.throttle import ThrottleConfig, ThrottleLock

logger = logging.getLogger(__name__)

T = TypeVar("T")


def run_throttled(
    cfg: Optional[ThrottleConfig],
    command: str,
    fn: Callable[[], T],
) -> T:
    """Run *fn* while holding the throttle lock for *command*.

    If throttling is disabled (cfg is None or cfg.enabled is False)
    *fn* is called directly.  If the lock cannot be acquired within
    the configured timeout a ``TimeoutError`` is raised.
    """
    if cfg is None or not cfg.enabled:
        return fn()

    lock = ThrottleLock(cfg, command)
    acquired = lock.acquire()
    if not acquired:
        raise TimeoutError(
            f"retryctl throttle: could not acquire lock for command "
            f"{command!r} within {cfg.timeout_seconds}s"
        )
    try:
        return fn()
    finally:
        lock.release()
