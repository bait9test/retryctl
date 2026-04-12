"""Middleware helpers for wiring fallback config into the retry pipeline."""
from __future__ import annotations

import logging
from typing import Any, Dict

from retryctl.fallback import FallbackConfig, FallbackResult, run_fallback
from retryctl.metrics import RunMetrics

log = logging.getLogger(__name__)


def parse_fallback(raw_config: Dict[str, Any]) -> FallbackConfig:
    """Extract and parse the [fallback] section from a raw config dict."""
    section = raw_config.get("fallback", {})
    if not isinstance(section, dict):
        raise TypeError("[fallback] config section must be a table")
    return FallbackConfig.from_dict(section)


def fallback_config_to_dict(cfg: FallbackConfig) -> Dict[str, Any]:
    """Serialise a FallbackConfig back to a plain dict (for audit / debug)."""
    return {
        "enabled": cfg.enabled,
        "command": cfg.command,
        "timeout": cfg.timeout,
        "capture_output": cfg.capture_output,
    }


def maybe_run_fallback(
    cfg: FallbackConfig,
    metrics: RunMetrics,
) -> FallbackResult:
    """Run the fallback only when the overall run has failed."""
    if metrics.succeeded:
        log.debug("Run succeeded — skipping fallback")
        return FallbackResult(ran=False)
    return run_fallback(cfg)


def describe_fallback(cfg: FallbackConfig) -> str:
    """Return a human-readable summary of the fallback configuration."""
    if not cfg.enabled or not cfg.command:
        return "fallback: disabled"
    timeout_str = f", timeout={cfg.timeout}s" if cfg.timeout else ""
    return f"fallback: {' '.join(cfg.command)}{timeout_str}"
