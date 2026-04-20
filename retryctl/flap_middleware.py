"""Middleware helpers for flap detection."""
from __future__ import annotations

import logging
from typing import Any, Dict

from retryctl.flap import FlapConfig, FlapDetected, FlapTracker, get_tracker

log = logging.getLogger(__name__)


def parse_flap(config: Dict[str, Any]) -> FlapConfig:
    """Extract [flap] section from a loaded config dict."""
    section = config.get("flap", {})
    if not isinstance(section, dict):
        raise TypeError(f"[flap] must be a table, got {type(section).__name__}")
    return FlapConfig.from_dict(section)


def flap_config_to_dict(cfg: FlapConfig) -> Dict[str, Any]:
    return {
        "enabled": cfg.enabled,
        "threshold": cfg.threshold,
        "window_seconds": cfg.window_seconds,
    }


def make_tracker(cfg: FlapConfig, key: str) -> FlapTracker:
    """Return a per-key FlapTracker (shared across calls with the same key)."""
    return get_tracker(cfg, key)


def on_attempt_complete(tracker: FlapTracker, success: bool) -> None:
    """Record the outcome of an attempt; raises FlapDetected if flapping."""
    try:
        tracker.record(success)
    except FlapDetected as exc:
        log.warning("flap: %s", exc)
        raise


def describe_flap(cfg: FlapConfig) -> str:
    if not cfg.enabled:
        return "flap detection disabled"
    return (
        f"flap detection enabled: threshold={cfg.threshold} "
        f"transitions in {cfg.window_seconds}s"
    )
