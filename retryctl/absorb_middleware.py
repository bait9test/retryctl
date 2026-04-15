"""absorb_middleware.py — helpers for wiring AbsorbConfig into the CLI pipeline."""
from __future__ import annotations

from retryctl.absorb import AbsorbConfig, check_absorbed, reset_absorb_state


def parse_absorb(cfg_dict: dict) -> AbsorbConfig:
    """Extract [absorb] section from a loaded config dict."""
    section = cfg_dict.get("absorb", {})
    if not isinstance(section, dict):
        raise TypeError(f"[absorb] must be a table, got {type(section).__name__}")
    return AbsorbConfig.from_dict(section)


def absorb_config_to_dict(cfg: AbsorbConfig) -> dict:
    return {
        "enabled": cfg.enabled,
        "threshold": cfg.threshold,
    }


def on_attempt_failure(cfg: AbsorbConfig, key: str) -> bool:
    """Call after each failed attempt.

    Returns True when the failure is absorbed (caller should treat as success).
    """
    return check_absorbed(cfg, key, failed=True)


def on_run_success(cfg: AbsorbConfig, key: str) -> None:
    """Call after a successful run to reset the consecutive-failure counter."""
    check_absorbed(cfg, key, failed=False)


def describe_absorb(cfg: AbsorbConfig) -> str:
    if not cfg.enabled:
        return "absorb: disabled"
    return f"absorb: threshold={cfg.threshold} consecutive failures"
