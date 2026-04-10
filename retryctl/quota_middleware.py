"""Middleware helpers for integrating quota checks into the retry loop."""
from __future__ import annotations

import logging
from typing import Any

from retryctl.quota import QuotaConfig, QuotaExceeded, check_quota, record_retry, reset_quota

log = logging.getLogger(__name__)


def parse_quota(raw_config: dict) -> QuotaConfig:
    """Extract quota config from the top-level config dict."""
    section = raw_config.get("quota", {})
    if not isinstance(section, dict):
        raise TypeError(f"[quota] must be a table, got {type(section).__name__}")
    return QuotaConfig.from_dict(section)


def quota_config_to_dict(cfg: QuotaConfig) -> dict:
    return {
        "enabled": cfg.enabled,
        "max_retries": cfg.max_retries,
        "window_seconds": cfg.window_seconds,
        "state_dir": cfg.state_dir,
        "key": cfg.key,
    }


def enforce_quota_gate(cfg: QuotaConfig, command: str) -> None:
    """Call before each retry attempt. Raises QuotaExceeded if the limit is hit."""
    try:
        used = check_quota(cfg, command)
        if cfg.enabled and cfg.max_retries > 0:
            log.debug("quota: %d/%d retries used in window", used, cfg.max_retries)
    except QuotaExceeded:
        log.warning(
            "quota: retry limit reached for command %r — blocking further retries",
            command,
        )
        raise


def on_retry_consumed(cfg: QuotaConfig, command: str) -> None:
    """Record a retry attempt after it has been dispatched."""
    record_retry(cfg, command)
    log.debug("quota: recorded retry for %r", command)


def on_run_success(cfg: QuotaConfig, command: str) -> None:
    """Optionally reset quota on success (configurable behaviour)."""
    reset_quota(cfg, command)
    log.debug("quota: reset quota for %r after success", command)
