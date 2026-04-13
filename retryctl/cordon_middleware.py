"""cordon_middleware.py — wiring helpers for the cordon feature."""
from __future__ import annotations

from typing import Any, Dict

from retryctl.cordon import CordonConfig, check_cordon, record_cordon_failure, reset_cordon


def parse_cordon(raw_config: Dict[str, Any]) -> CordonConfig:
    """Build a CordonConfig from the [cordon] section of a config dict."""
    section = raw_config.get("cordon", {})
    if not isinstance(section, dict):
        raise TypeError("[cordon] must be a table")
    return CordonConfig.from_dict(section)


def cordon_config_to_dict(cfg: CordonConfig) -> Dict[str, Any]:
    return {
        "enabled": cfg.enabled,
        "threshold": cfg.threshold,
        "window_seconds": cfg.window_seconds,
        "duration_seconds": cfg.duration_seconds,
        "key": cfg.key,
        "lock_dir": cfg.lock_dir,
    }


def enforce_cordon_gate(cfg: CordonConfig, key: str) -> None:
    """Call before each attempt; raises CordonBlocked if cordoned."""
    check_cordon(cfg, key)


def on_attempt_failure(cfg: CordonConfig, key: str) -> None:
    """Call after each failed attempt to accumulate failure count."""
    record_cordon_failure(cfg, key)


def on_run_success(cfg: CordonConfig, key: str) -> None:
    """Call on overall run success to clear cordon state."""
    reset_cordon(cfg, key)


def describe_cordon(cfg: CordonConfig) -> str:
    if not cfg.enabled:
        return "cordon: disabled"
    return (
        f"cordon: threshold={cfg.threshold} failures "
        f"in {cfg.window_seconds}s → block for {cfg.duration_seconds}s"
    )
