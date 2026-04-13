"""Middleware helpers for the pacing feature."""
from __future__ import annotations

import logging
from typing import Any, Dict

from retryctl.pacing import PacingConfig, PacingTracker

log = logging.getLogger(__name__)


def parse_pacing(config_dict: Dict[str, Any]) -> PacingConfig:
    """Extract [pacing] section from the top-level config mapping."""
    section = config_dict.get("pacing", {})
    if not isinstance(section, dict):
        raise TypeError("[pacing] must be a TOML table")
    return PacingConfig.from_dict(section)


def pacing_config_to_dict(cfg: PacingConfig) -> Dict[str, Any]:
    return {
        "enabled": cfg.enabled,
        "min_interval_s": cfg.min_interval_s,
    }


def before_attempt(tracker: PacingTracker, attempt: int) -> float:
    """Wait for pacing gap (if any) then record the attempt start time.

    Returns the number of seconds we actually slept.
    """
    slept = tracker.wait_if_needed()
    if slept > 0:
        log.debug("pacing: slept %.3fs before attempt %d", slept, attempt)
    tracker.record_attempt_start()
    return slept


def on_run_complete(tracker: PacingTracker) -> None:
    """Reset tracker state at the end of a run (success or final failure)."""
    tracker.reset()


def describe_pacing(cfg: PacingConfig) -> str:
    if not cfg.enabled:
        return "pacing disabled"
    return f"pacing enabled — min interval {cfg.min_interval_s}s between attempts"
