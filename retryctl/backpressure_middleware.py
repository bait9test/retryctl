"""Middleware helpers for integrating backpressure into the retry loop."""
from __future__ import annotations

from typing import Any

from retryctl.backpressure import BackpressureConfig, apply_backpressure


def parse_backpressure(config_dict: dict) -> BackpressureConfig:
    """Extract and parse the [backpressure] section from a config mapping."""
    raw = config_dict.get("backpressure", {})
    if not isinstance(raw, dict):
        raise TypeError("[backpressure] must be a TOML table")
    return BackpressureConfig.from_dict(raw)


def backpressure_config_to_dict(cfg: BackpressureConfig) -> dict[str, Any]:
    """Serialise a BackpressureConfig back to a plain dict (for audit/debug)."""
    return {
        "enabled": cfg.enabled,
        "source_file": cfg.source_file,
        "source_cmd": cfg.source_cmd,
        "threshold": cfg.threshold,
        "penalty_seconds": cfg.penalty_seconds,
        "max_penalty_seconds": cfg.max_penalty_seconds,
    }


def maybe_apply_backpressure(cfg: BackpressureConfig, attempt: int) -> None:
    """Call apply_backpressure only when backpressure is enabled.

    Intended to be dropped into the retry loop just before each attempt:

        for attempt in range(max_attempts):
            maybe_apply_backpressure(bp_cfg, attempt)
            result = run_command(...)
    """
    if not cfg.enabled:
        return
    apply_backpressure(cfg, attempt)


def describe_backpressure(cfg: BackpressureConfig) -> str:
    """Return a human-readable summary of the backpressure configuration."""
    if not cfg.enabled:
        return "backpressure: disabled"
    source = cfg.source_file or cfg.source_cmd or "(none)"
    return (
        f"backpressure: enabled | source={source!r} | "
        f"threshold={cfg.threshold} | penalty={cfg.penalty_seconds}s "
        f"(max {cfg.max_penalty_seconds}s)"
    )
