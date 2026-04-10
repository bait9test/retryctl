"""Middleware helpers for applying the concurrency guard around a retry run."""

from __future__ import annotations

import logging
from typing import Callable, Any, Optional

from retryctl.concurrency import ConcurrencyConfig, ConcurrencyLock, ConcurrencyBlocked

log = logging.getLogger(__name__)


def parse_concurrency(raw: dict) -> ConcurrencyConfig:
    """Build a ConcurrencyConfig from the [concurrency] section of a config dict."""
    section = raw.get("concurrency", {})
    if not isinstance(section, dict):
        raise TypeError(f"[concurrency] must be a table, got {type(section).__name__}")
    return ConcurrencyConfig.from_dict(section)


def concurrency_config_to_dict(cfg: ConcurrencyConfig) -> dict:
    return {
        "enabled": cfg.enabled,
        "key": cfg.key,
        "lock_dir": cfg.lock_dir,
        "wait": cfg.wait,
        "timeout_seconds": cfg.timeout_seconds,
    }


def run_with_concurrency_guard(
    cfg: ConcurrencyConfig,
    command_key: str,
    fn: Callable[[], Any],
) -> Any:
    """Run *fn* while holding the concurrency lock for *command_key*.

    If ``cfg.enabled`` is False the function is called directly.
    Raises ``ConcurrencyBlocked`` when the lock cannot be obtained and
    ``cfg.wait`` is False.
    """
    if not cfg.enabled:
        return fn()

    effective_key = cfg.key or command_key
    log.debug("concurrency guard active, key=%r wait=%s", effective_key, cfg.wait)

    with ConcurrencyLock(cfg, effective_key):
        return fn()
