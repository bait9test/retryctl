"""Middleware helpers for integrating WatermarkTracker into the retry loop."""
from __future__ import annotations

import logging
from typing import Any

from retryctl.watermark import WatermarkConfig, WatermarkTracker, WatermarkBreached

log = logging.getLogger(__name__)


def parse_watermark(config_dict: dict) -> WatermarkConfig:
    """Extract [watermark] section from the top-level config dict."""
    section = config_dict.get("watermark", {})
    if not isinstance(section, dict):
        raise TypeError(f"[watermark] must be a table, got {type(section).__name__}")
    return WatermarkConfig.from_dict(section)


def watermark_config_to_dict(cfg: WatermarkConfig) -> dict:
    return {
        "enabled": cfg.enabled,
        "threshold": cfg.threshold,
        "reset_on_success": cfg.reset_on_success,
    }


def on_attempt_failure(tracker: WatermarkTracker) -> None:
    """Call after each failed attempt; raises WatermarkBreached when threshold is hit."""
    tracker.record_failure()


def on_run_success(tracker: WatermarkTracker) -> None:
    """Call after a successful run to reset the consecutive counter."""
    tracker.record_success()


def describe_watermark(cfg: WatermarkConfig) -> str:
    if not cfg.enabled:
        return "watermark: disabled"
    return (
        f"watermark: enabled (threshold={cfg.threshold}, "
        f"reset_on_success={cfg.reset_on_success})"
    )
