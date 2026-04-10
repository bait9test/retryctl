"""Middleware helpers for wiring BudgetTracker into the retry loop."""

from __future__ import annotations

import logging
from typing import Any, Dict

from retryctl.budget import BudgetConfig, BudgetTracker, BudgetExceeded

logger = logging.getLogger(__name__)


def parse_budget(raw: Dict[str, Any]) -> BudgetConfig:
    """Extract [budget] section from a raw config dict."""
    section = raw.get("budget", {})
    if not isinstance(section, dict):
        raise TypeError("[budget] config must be a table")
    return BudgetConfig.from_dict(section)


def budget_config_to_dict(cfg: BudgetConfig) -> Dict[str, Any]:
    return {
        "enabled": cfg.enabled,
        "max_retries": cfg.max_retries,
        "window_seconds": cfg.window_seconds,
        "key": cfg.key,
    }


def enforce_budget_gate(tracker: BudgetTracker, attempt: int) -> None:
    """Call before each retry attempt; raises BudgetExceeded if exhausted."""
    if not tracker.config.enabled:
        return
    try:
        tracker.check_or_raise()
    except BudgetExceeded as exc:
        logger.warning(
            "retry budget gate blocked attempt %d for key '%s': %s",
            attempt,
            tracker.config.key,
            exc,
        )
        raise


def on_retry_consumed(tracker: BudgetTracker) -> None:
    """Record that one retry was consumed; call after a failed attempt."""
    tracker.record_retry()
    remaining = tracker.remaining()
    if tracker.config.enabled:
        logger.debug(
            "retry budget: recorded attempt for key '%s', %d remaining in window",
            tracker.config.key,
            remaining,
        )
