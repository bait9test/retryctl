"""brake_middleware.py – wiring helpers for the brake feature."""
from __future__ import annotations

import logging
from typing import Any, Dict

from retryctl.brake import BrakeConfig, BrakeState

log = logging.getLogger(__name__)


def parse_brake(config: Dict[str, Any]) -> BrakeConfig:
    """Extract [brake] section from a parsed config dict."""
    section = config.get("brake")
    if section is None:
        return BrakeConfig()
    return BrakeConfig.from_dict(section)


def brake_config_to_dict(cfg: BrakeConfig) -> Dict[str, Any]:
    return {
        "enabled": cfg.enabled,
        "threshold": cfg.threshold,
        "step_ms": cfg.step_ms,
        "max_ms": cfg.max_ms,
    }


def make_state() -> BrakeState:
    return BrakeState()


def on_attempt_failure(cfg: BrakeConfig, state: BrakeState) -> int:
    """Call after each failed attempt; returns extra delay ms to apply."""
    if not cfg.enabled:
        return 0
    return state.record_failure(cfg)


def on_run_success(cfg: BrakeConfig, state: BrakeState) -> None:
    """Call when the overall run succeeds."""
    if cfg.enabled:
        state.record_success()


def describe_brake(cfg: BrakeConfig) -> str:
    if not cfg.enabled:
        return "brake: disabled"
    return (
        f"brake: enabled (threshold={cfg.threshold}, "
        f"step={cfg.step_ms}ms, max={cfg.max_ms}ms)"
    )
