"""Middleware helpers for the pulse (heartbeat) feature."""
from __future__ import annotations

from typing import Any

from retryctl.pulse import PulseConfig, PulseEmitter, describe_pulse


def parse_pulse(config_dict: dict) -> PulseConfig:
    """Extract and parse the [pulse] section from a config dict."""
    raw = config_dict.get("pulse", {})
    if not isinstance(raw, dict):
        raise TypeError(f"[pulse] must be a table, got {type(raw).__name__}")
    return PulseConfig.from_dict(raw)


def pulse_config_to_dict(cfg: PulseConfig) -> dict[str, Any]:
    """Serialise a PulseConfig back to a plain dict (for auditing / debug)."""
    return {
        "enabled": cfg.enabled,
        "interval_seconds": cfg.interval_seconds,
        "channel": cfg.channel,
        "message": cfg.message,
    }


def make_emitter(cfg: PulseConfig) -> PulseEmitter:
    """Convenience factory so callers don't import PulseEmitter directly."""
    return PulseEmitter(config=cfg)


def describe(cfg: PulseConfig) -> str:
    return describe_pulse(cfg)
