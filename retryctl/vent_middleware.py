"""vent_middleware.py – parse config and integrate VentTracker into the retry loop."""
from __future__ import annotations

from typing import Any

from retryctl.vent import VentConfig, VentTracker, VentOpen


def parse_vent(config: dict) -> VentConfig:
    """Extract [vent] section from the full config dict."""
    section = config.get("vent", {})
    if not isinstance(section, dict):
        raise TypeError(f"[vent] must be a table, got {type(section).__name__}")
    return VentConfig.from_dict(section)


def vent_config_to_dict(cfg: VentConfig) -> dict:
    return {
        "enabled": cfg.enabled,
        "threshold": cfg.threshold,
        "window": cfg.window,
        "cooldown_seconds": cfg.cooldown_seconds,
    }


def make_tracker(cfg: VentConfig) -> VentTracker:
    return VentTracker(config=cfg)


def on_attempt_failure(tracker: VentTracker) -> None:
    """Call after each failed attempt."""
    tracker.record_failure()


def on_run_success(tracker: VentTracker) -> None:
    """Call when the overall run succeeds."""
    tracker.record_success()


def before_attempt(tracker: VentTracker) -> None:
    """Call before each attempt; raises VentOpen if vent is active."""
    tracker.check()


def describe_vent(cfg: VentConfig) -> str:
    if not cfg.enabled:
        return "vent: disabled"
    return (
        f"vent: threshold={cfg.threshold:.0%}, "
        f"window={cfg.window}, "
        f"cooldown={cfg.cooldown_seconds}s"
    )
