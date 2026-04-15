"""Middleware helpers for the canary feature."""
from __future__ import annotations

import logging
from typing import Any, Dict

from retryctl.canary import CanaryBlocked, CanaryConfig, run_canary

log = logging.getLogger(__name__)


def parse_canary(raw_config: Dict[str, Any]) -> CanaryConfig:
    """Extract [canary] section from a raw config dict."""
    section = raw_config.get("canary", {})
    if not isinstance(section, dict):
        raise TypeError("[canary] must be a TOML table")
    return CanaryConfig.from_dict(section)


def canary_config_to_dict(cfg: CanaryConfig) -> Dict[str, Any]:
    """Serialise a CanaryConfig back to a plain dict (for auditing / replay)."""
    return {
        "enabled": cfg.enabled,
        "command": cfg.command,
        "timeout": cfg.timeout,
        "skip_on_failure": cfg.skip_on_failure,
    }


def before_attempt(cfg: CanaryConfig, attempt: int) -> bool:
    """Gate called before each attempt.

    Returns True if the attempt should proceed, False if it should be skipped.
    Raises CanaryBlocked if skip_on_failure is False and the canary fails.
    """
    if not cfg.enabled:
        return True
    healthy = run_canary(cfg)
    if not healthy:
        log.info("attempt %d skipped — canary check did not pass", attempt)
    return healthy


def describe_canary(cfg: CanaryConfig) -> str:
    if not cfg.enabled:
        return "canary: disabled"
    cmd_str = " ".join(cfg.command) if cfg.command else "(none)"
    mode = "skip" if cfg.skip_on_failure else "abort"
    return f"canary: command={cmd_str!r} timeout={cfg.timeout}s on_failure={mode}"
