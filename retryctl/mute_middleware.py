"""mute_middleware.py — wire MuteConfig into the retryctl pipeline."""
from __future__ import annotations

import logging
from typing import Any, Dict

from retryctl.mute import MuteConfig, is_muted, mute_config_summary

log = logging.getLogger(__name__)


def parse_mute(config: Dict[str, Any]) -> MuteConfig:
    """Build a MuteConfig from the top-level config dict."""
    raw = config.get("mute")
    if raw is None:
        return MuteConfig()
    return MuteConfig.from_dict(raw)


def mute_config_to_dict(cfg: MuteConfig) -> Dict[str, Any]:
    return {
        "enabled": cfg.enabled,
        "exit_codes": list(cfg.exit_codes),
        "patterns": list(cfg.patterns),
        "suppress_alerts": cfg.suppress_alerts,
        "suppress_output": cfg.suppress_output,
    }


def check_mute(
    cfg: MuteConfig,
    exit_code: int,
    output: str = "",
) -> bool:
    """Check whether the run result should be muted; logs a debug line when muted."""
    if not cfg.enabled:
        return False
    muted = is_muted(cfg, exit_code, output)
    if muted:
        log.debug(
            "mute: suppressing result for exit_code=%d (suppress_alerts=%s, suppress_output=%s)",
            exit_code,
            cfg.suppress_alerts,
            cfg.suppress_output,
        )
    return muted


def describe_mute(cfg: MuteConfig) -> str:
    summary = mute_config_summary(cfg)
    return summary if summary is not None else "mute(disabled)"
