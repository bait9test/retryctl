"""veil_middleware.py — Wiring helpers for the veil drop-rate feature."""
from __future__ import annotations

import logging
from typing import Any

from retryctl.veil import VeilConfig, VeilTracker, VeiledAttempt

log = logging.getLogger(__name__)


def parse_veil(config: dict[str, Any]) -> VeilConfig:
    """Extract [veil] section from a raw config dict."""
    section = config.get("veil", {})
    if not isinstance(section, dict):
        raise TypeError(f"[veil] must be a table, got {type(section).__name__}")
    return VeilConfig.from_dict(section)


def veil_config_to_dict(cfg: VeilConfig) -> dict[str, Any]:
    """Serialise a VeilConfig back to a plain dict (for audit/debug)."""
    return {
        "enabled": cfg.enabled,
        "drop_rate": cfg.drop_rate,
        "seed": cfg.seed,
    }


def make_tracker(cfg: VeilConfig) -> VeilTracker:
    return VeilTracker(config=cfg)


def before_attempt(tracker: VeilTracker, attempt: int) -> None:
    """Call before each attempt; raises VeiledAttempt if the attempt should be dropped."""
    try:
        tracker.check(attempt)
    except VeiledAttempt as exc:
        log.debug("veil: %s", exc)
        raise


def describe_veil(cfg: VeilConfig) -> str:
    if not cfg.enabled:
        return "veil disabled"
    return f"veil enabled — drop_rate={cfg.drop_rate:.2%}" + (
        f", seed={cfg.seed}" if cfg.seed is not None else ""
    )
