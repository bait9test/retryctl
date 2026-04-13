"""Middleware helpers for the tide adaptive-delay feature."""
from __future__ import annotations

from typing import Any

from retryctl.tide import TideConfig, TideState, apply_tide


def parse_tide(config: dict[str, Any]) -> TideConfig:
    """Extract [tide] section from a raw config dict."""
    raw = config.get("tide", {})
    if not isinstance(raw, dict):
        raise TypeError(f"[tide] must be a table, got {type(raw).__name__}")
    return TideConfig.from_dict(raw)


def tide_config_to_dict(cfg: TideConfig) -> dict[str, Any]:
    return {
        "enabled": cfg.enabled,
        "threshold": cfg.threshold,
        "multiplier": cfg.multiplier,
        "max_multiplier": cfg.max_multiplier,
    }


def on_attempt_failure(state: TideState, cfg: TideConfig) -> float:
    """Call after each failed attempt; returns the updated multiplier."""
    return state.record_failure(cfg)


def on_run_success(state: TideState) -> None:
    """Call after a successful run to reset the tide state."""
    state.record_success()


def scaled_delay(base: float, state: TideState, cfg: TideConfig) -> float:
    """Return the tide-adjusted delay for the next attempt."""
    return apply_tide(base, state, cfg)


def describe_tide(cfg: TideConfig) -> str:
    if not cfg.enabled:
        return "tide: disabled"
    return (
        f"tide: enabled | threshold={cfg.threshold} failures "
        f"| multiplier={cfg.multiplier}x (max {cfg.max_multiplier}x)"
    )
