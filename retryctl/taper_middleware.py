"""Middleware helpers for the taper feature.

Taper gradually reduces the retry delay multiplier after a sustained run
of consecutive failures, preventing runaway back-off in long-lived processes.
"""
from __future__ import annotations

import logging
from typing import Any

from retryctl.taper import TaperConfig, TaperState, from_dict as _taper_from_dict

log = logging.getLogger(__name__)


def parse_taper(raw: dict[str, Any]) -> TaperConfig:
    """Extract and validate a TaperConfig from a raw config dict."""
    section = raw.get("taper", {})
    if not isinstance(section, dict):
        raise TypeError(f"[taper] must be a table, got {type(section).__name__}")
    return _taper_from_dict(section)


def taper_config_to_dict(cfg: TaperConfig) -> dict[str, Any]:
    """Serialise a TaperConfig back to a plain dict (round-trip helper)."""
    return {
        "enabled": cfg.enabled,
        "threshold": cfg.threshold,
        "factor": cfg.factor,
        "min_multiplier": cfg.min_multiplier,
        "reset_on_success": cfg.reset_on_success,
    }


def make_state(cfg: TaperConfig) -> TaperState:
    """Create a fresh TaperState bound to *cfg*."""
    return TaperState(cfg)


def on_attempt_failure(state: TaperState, attempt: int) -> float:
    """Record a failure and return the current delay multiplier.

    Call this after each failed attempt so the state machine can decide
    whether the taper threshold has been reached.
    """
    state.record_failure(attempt)
    multiplier = state.current_multiplier()
    if state.is_tapered():
        log.debug(
            "taper active after %d consecutive failures — multiplier=%.3f",
            state.consecutive_failures,
            multiplier,
        )
    return multiplier


def on_run_success(state: TaperState) -> None:
    """Reset taper state when the overall run eventually succeeds."""
    state.record_success()
    log.debug("taper reset after successful run")


def describe_taper(cfg: TaperConfig) -> str:
    """Return a human-readable summary of the taper configuration."""
    if not cfg.enabled:
        return "taper: disabled"
    return (
        f"taper: enabled — threshold={cfg.threshold} failures, "
        f"factor={cfg.factor}, min_multiplier={cfg.min_multiplier}"
    )
