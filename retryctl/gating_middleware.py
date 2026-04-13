"""gating_middleware.py — helpers to wire GatingConfig into the CLI / config pipeline."""
from __future__ import annotations

import logging
from typing import Any, Dict

from retryctl.gating import GatingConfig, GateBlocked, check_gate

log = logging.getLogger(__name__)


def parse_gating(config: Dict[str, Any]) -> GatingConfig:
    """Extract [gating] section from the top-level config dict."""
    section = config.get("gating", {})
    if not isinstance(section, dict):
        raise TypeError("[gating] section must be a TOML table")
    return GatingConfig.from_dict(section)


def gating_config_to_dict(cfg: GatingConfig) -> Dict[str, Any]:
    return {
        "enabled": cfg.enabled,
        "command": cfg.command,
        "timeout": cfg.timeout,
        "allow_on_error": cfg.allow_on_error,
    }


def before_attempt(cfg: GatingConfig, attempt: int) -> None:
    """Call before each retry attempt. Raises GateBlocked to abort the attempt."""
    if not cfg.enabled:
        return
    log.debug("gating: running gate check before attempt %d", attempt)
    check_gate(cfg)


def describe_gating(cfg: GatingConfig) -> str:
    if not cfg.enabled:
        return "gating disabled"
    cmd_str = " ".join(cfg.command) if cfg.command else "<none>"
    return (
        f"gating enabled: command={cmd_str!r} "
        f"timeout={cfg.timeout}s "
        f"allow_on_error={cfg.allow_on_error}"
    )
