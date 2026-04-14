"""Middleware helpers for shadow mode integration."""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from retryctl.shadow import ShadowConfig, ShadowResult, compare_shadow, run_shadow

log = logging.getLogger(__name__)


def parse_shadow(raw_config: Dict[str, Any]) -> ShadowConfig:
    """Extract and parse [shadow] section from a raw config dict."""
    section = raw_config.get("shadow", {})
    if not isinstance(section, dict):
        raise TypeError("[shadow] config section must be a table")
    return ShadowConfig.from_dict(section)


def shadow_config_to_dict(cfg: ShadowConfig) -> Dict[str, Any]:
    return {
        "enabled": cfg.enabled,
        "command": cfg.command,
        "timeout": cfg.timeout,
        "log_divergence": cfg.log_divergence,
    }


def maybe_run_shadow(
    cfg: ShadowConfig, primary_exit_code: int
) -> Optional[ShadowResult]:
    """Run shadow command and log divergence; returns result or None."""
    if not cfg.enabled:
        return None
    result = run_shadow(cfg)
    if result is not None:
        agreed = compare_shadow(primary_exit_code, result, cfg)
        if agreed:
            log.debug("shadow command agreed with primary (exit=%d)", primary_exit_code)
    return result


def describe_shadow(cfg: ShadowConfig) -> str:
    if not cfg.enabled:
        return "shadow: disabled"
    cmd_str = " ".join(cfg.command) if cfg.command else "(none)"
    return (
        f"shadow: enabled | command={cmd_str!r} | timeout={cfg.timeout}s"
        f" | log_divergence={cfg.log_divergence}"
    )
