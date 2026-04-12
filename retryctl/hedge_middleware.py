"""Middleware helpers for the hedge feature."""
from __future__ import annotations

from typing import Any, Dict

from retryctl.hedge import HedgeConfig, HedgeResult, from_dict, run_hedged


def parse_hedge(config: Dict[str, Any]) -> HedgeConfig:
    """Extract hedge section from the top-level config dict."""
    section = config.get("hedge", {})
    if not isinstance(section, dict):
        raise TypeError("[hedge] config section must be a table")
    return from_dict(section)


def hedge_config_to_dict(cfg: HedgeConfig) -> Dict[str, Any]:
    return {
        "enabled": cfg.enabled,
        "delay_ms": cfg.delay_ms,
        "max_hedges": cfg.max_hedges,
    }


def maybe_run_hedged(
    cmd,
    cfg: HedgeConfig,
    *,
    env=None,
    timeout=None,
):
    """Run *cmd* hedged if cfg.enabled, otherwise run it directly.

    Returns a HedgeResult in both cases so callers have a uniform interface.
    """
    if not cfg.enabled:
        import subprocess
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            timeout=timeout,
        )
        return HedgeResult(
            returncode=proc.returncode,
            stdout=proc.stdout,
            stderr=proc.stderr,
            winner_index=0,
        )
    return run_hedged(cmd, cfg, env=env, timeout=timeout)


def describe_hedge(cfg: HedgeConfig) -> str:
    if not cfg.enabled:
        return "hedge: disabled"
    return (
        f"hedge: enabled — speculative attempt after {cfg.delay_ms} ms, "
        f"max_hedges={cfg.max_hedges}"
    )
