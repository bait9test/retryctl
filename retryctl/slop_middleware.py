"""slop_middleware.py — wiring helpers for the slop tolerance feature."""
from __future__ import annotations

import logging
from typing import Any, Dict

from retryctl.slop import SlopConfig, SlopTracker, SlopAbsorbed

log = logging.getLogger(__name__)


def parse_slop(config: Dict[str, Any]) -> SlopConfig:
    """Extract [slop] section from a raw config dict."""
    section = config.get("slop", {})
    if not isinstance(section, dict):
        raise TypeError(f"[slop] must be a table, got {type(section).__name__}")
    return SlopConfig.from_dict(section)


def slop_config_to_dict(cfg: SlopConfig) -> Dict[str, Any]:
    return {
        "enabled": cfg.enabled,
        "tolerance_codes": list(cfg.tolerance_codes),
        "window": cfg.window,
    }


def make_tracker(cfg: SlopConfig) -> SlopTracker:
    return SlopTracker(cfg)


def on_attempt_marginal(tracker: SlopTracker, exit_code: int) -> bool:
    """Call after a failed attempt.  Returns True if the failure was absorbed.

    Callers should skip incrementing the retry counter when True is returned.
    """
    if not tracker._cfg.enabled:
        return False
    try:
        tracker.check(exit_code)
        return False
    except SlopAbsorbed as exc:
        log.debug(
            "slop absorbed exit_code=%d remaining_tolerance=%d",
            exc.exit_code,
            exc.remaining,
        )
        return True


def on_run_success(tracker: SlopTracker) -> None:
    """Reset marginal counter on a clean run."""
    tracker.reset()


def describe_slop(cfg: SlopConfig) -> str:
    if not cfg.enabled:
        return "slop: disabled"
    return (
        f"slop: window={cfg.window} "
        f"tolerance_codes={cfg.tolerance_codes}"
    )
