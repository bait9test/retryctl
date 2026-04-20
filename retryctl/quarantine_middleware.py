"""Middleware helpers for the quarantine feature."""
from __future__ import annotations

import logging
from typing import Any, Dict

from retryctl.quarantine import (
    QuarantineConfig,
    QuarantineBlocked,
    check_quarantine,
    record_failure,
    record_success,
)

log = logging.getLogger(__name__)


def parse_quarantine(config: Dict[str, Any]) -> QuarantineConfig:
    """Build a QuarantineConfig from the raw [quarantine] TOML section."""
    section = config.get("quarantine", {})
    if not isinstance(section, dict):
        raise TypeError("[quarantine] must be a TOML table")
    return QuarantineConfig.from_dict(section)


def quarantine_config_to_dict(cfg: QuarantineConfig) -> Dict[str, Any]:
    return {
        "enabled": cfg.enabled,
        "threshold": cfg.threshold,
        "window_seconds": cfg.window_seconds,
        "duration_seconds": cfg.duration_seconds,
        "key": cfg.key,
    }


def before_attempt(cfg: QuarantineConfig) -> None:
    """Call before each attempt; raises QuarantineBlocked if quarantined."""
    try:
        check_quarantine(cfg)
    except QuarantineBlocked as exc:
        log.warning("quarantine: %s", exc)
        raise


def on_attempt_failure(cfg: QuarantineConfig) -> None:
    """Record a failure; may trigger quarantine."""
    record_failure(cfg)
    if cfg.enabled:
        log.debug("quarantine: recorded failure for key '%s'", cfg.key)


def on_run_success(cfg: QuarantineConfig) -> None:
    """Clear failure state on a successful run."""
    record_success(cfg)
    if cfg.enabled:
        log.debug("quarantine: cleared failure state for key '%s'", cfg.key)


def describe_quarantine(cfg: QuarantineConfig) -> str:
    if not cfg.enabled:
        return "quarantine: disabled"
    return (
        f"quarantine: key='{cfg.key}' threshold={cfg.threshold} "
        f"window={cfg.window_seconds}s duration={cfg.duration_seconds}s"
    )
