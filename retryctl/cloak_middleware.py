"""Middleware helpers for the cloak feature."""
from __future__ import annotations

import logging
from typing import Any

from retryctl.cloak import CloakConfig, CloakTracker, CloakedAttempt

log = logging.getLogger(__name__)


def parse_cloak(config: dict[str, Any]) -> CloakConfig:
    """Extract [cloak] section from the top-level config dict."""
    raw = config.get("cloak", {})
    if not isinstance(raw, dict):
        raise TypeError(f"[cloak] must be a dict, got {type(raw).__name__}")
    return CloakConfig.from_dict(raw)


def cloak_config_to_dict(cfg: CloakConfig) -> dict[str, Any]:
    return {
        "enabled": cfg.enabled,
        "mask_rate": cfg.mask_rate,
        "seed": cfg.seed,
        "tag": cfg.tag,
    }


def make_tracker(cfg: CloakConfig) -> CloakTracker:
    return CloakTracker(config=cfg)


def before_attempt(tracker: CloakTracker, attempt: int) -> None:
    """Call before each attempt; raises CloakedAttempt if masked."""
    if tracker.is_cloaked(attempt):
        log.debug("attempt %d cloaked (tag=%s)", attempt, tracker.config.tag)
        raise CloakedAttempt(attempt, tracker.config.tag)


def describe_cloak(cfg: CloakConfig) -> str:
    if not cfg.enabled:
        return "cloak: disabled"
    return (
        f"cloak: enabled  mask_rate={cfg.mask_rate:.0%}  "
        f"tag='{cfg.tag}'"
        + (f"  seed={cfg.seed}" if cfg.seed is not None else "")
    )
