"""Middleware helpers for the splay feature."""
from __future__ import annotations

import logging
from typing import Any

from retryctl.splay import SplayConfig, apply_splay, compute_splay, from_dict

log = logging.getLogger(__name__)


def parse_splay(config_dict: dict[str, Any]) -> SplayConfig:
    """Extract and parse the [splay] section from a raw config dict."""
    raw = config_dict.get("splay", {})
    if not isinstance(raw, dict):
        raise TypeError(f"[splay] must be a table, got {type(raw).__name__}")
    return from_dict(raw)


def splay_config_to_dict(cfg: SplayConfig) -> dict[str, Any]:
    """Serialise a SplayConfig back to a plain dict (for audit / replay)."""
    return {
        "enabled": cfg.enabled,
        "max_seconds": cfg.max_seconds,
        "seed": cfg.seed,
    }


def maybe_apply_splay(cfg: SplayConfig) -> float:
    """Apply splay delay if enabled; log the chosen delay and return it."""
    if not cfg.enabled or cfg.max_seconds <= 0:
        return 0.0
    delay = compute_splay(cfg)
    log.debug("splay: sleeping %.3fs before first attempt", delay)
    import time
    time.sleep(delay)
    log.debug("splay: done sleeping")
    return delay


def describe_splay(cfg: SplayConfig) -> str:
    """Return a human-readable description of the splay configuration."""
    if not cfg.enabled:
        return "splay disabled"
    return f"splay up to {cfg.max_seconds:.1f}s"
