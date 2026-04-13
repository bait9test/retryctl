"""spillover_middleware.py — helpers for wiring SpilloverConfig into the retry loop."""
from __future__ import annotations

import logging
from typing import Any, Dict, List

from retryctl.spillover import SpilloverConfig, SpilloverResult, run_spillover

log = logging.getLogger(__name__)


def parse_spillover(raw_config: Dict[str, Any]) -> SpilloverConfig:
    """Extract [spillover] section from the top-level config dict."""
    section = raw_config.get("spillover", {})
    if not isinstance(section, dict):
        raise TypeError("[spillover] config section must be a table")
    return SpilloverConfig.from_dict(section)


def spillover_config_to_dict(cfg: SpilloverConfig) -> Dict[str, Any]:
    return {
        "enabled": cfg.enabled,
        "threshold": cfg.threshold,
        "command": cfg.command,
        "capture_output": cfg.capture_output,
        "timeout": cfg.timeout,
    }


def maybe_run_spillover(
    cfg: SpilloverConfig,
    attempt: int,
    original_command: List[str],
) -> SpilloverResult:
    """Invoke spillover logic and log outcome; safe to call unconditionally."""
    result = run_spillover(cfg, attempt, original_command)
    if result.triggered:
        if result.returncode == 0:
            log.info("spillover command succeeded (rc=0)")
        elif result.returncode is not None:
            log.warning("spillover command exited with rc=%d", result.returncode)
        if result.stderr:
            log.debug("spillover stderr: %s", result.stderr.strip())
    return result


def describe_spillover(cfg: SpilloverConfig) -> str:
    if not cfg.enabled:
        return "spillover: disabled"
    cmd_str = " ".join(cfg.command) if cfg.command else "<none>"
    return f"spillover: enabled (threshold={cfg.threshold}, command={cmd_str!r})"
