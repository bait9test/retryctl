"""drain_middleware.py — helpers for wiring DrainConfig into the CLI/config layer."""
from __future__ import annotations

import logging
from typing import Any, Dict

from retryctl.drain import DrainConfig, DrainResult

log = logging.getLogger(__name__)


def parse_drain(raw_config: Dict[str, Any]) -> DrainConfig:
    """Extract and parse the ``[drain]`` section from a raw config dict."""
    section = raw_config.get("drain", {})
    if not isinstance(section, dict):
        raise TypeError(f"[drain] must be a table, got {type(section).__name__}")
    return DrainConfig.from_dict(section)


def drain_config_to_dict(cfg: DrainConfig) -> Dict[str, Any]:
    """Serialise a :class:`DrainConfig` back to a plain dict (for audit/debug)."""
    return {
        "enabled": cfg.enabled,
        "max_lines": cfg.max_lines,
    }


def log_drain_result(result: DrainResult, *, attempt: int) -> None:
    """Emit captured lines at DEBUG level, prefixed by stream name."""
    for line in result.stdout_lines:
        log.debug("[attempt %d] stdout: %s", attempt, line)
    for line in result.stderr_lines:
        log.debug("[attempt %d] stderr: %s", attempt, line)


def describe_drain(cfg: DrainConfig) -> str:
    """Return a human-readable summary of the drain configuration."""
    if not cfg.enabled:
        return "drain: disabled"
    cap = f", max_lines={cfg.max_lines}" if cfg.max_lines else ""
    return f"drain: enabled{cap}"
