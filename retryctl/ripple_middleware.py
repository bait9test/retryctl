"""ripple_middleware.py — helpers for wiring RippleConfig into the run pipeline."""
from __future__ import annotations

from typing import Any, Dict

from retryctl.ripple import RippleConfig, fire_ripple


def parse_ripple(config: Dict[str, Any]) -> RippleConfig:
    """Extract and parse the [ripple] section from the top-level config dict."""
    raw = config.get("ripple", {})
    if not isinstance(raw, dict):
        raise TypeError(f"[ripple] section must be a table, got {type(raw).__name__}")
    return RippleConfig.from_dict(raw)


def ripple_config_to_dict(cfg: RippleConfig) -> Dict[str, Any]:
    """Serialise a RippleConfig back to a plain dict (e.g. for audit/snapshot)."""
    return {
        "enabled": cfg.enabled,
        "command": cfg.command,
        "on_failure": cfg.on_failure,
        "on_success": cfg.on_success,
        "timeout": cfg.timeout,
    }


def on_run_complete(cfg: RippleConfig, *, succeeded: bool) -> None:
    """Call after every run to conditionally fire the ripple signal."""
    fire_ripple(cfg, succeeded=succeeded)


def describe_ripple(cfg: RippleConfig) -> str:
    """Return a human-readable summary of the ripple configuration."""
    if not cfg.enabled:
        return "ripple: disabled"
    triggers = []
    if cfg.on_failure:
        triggers.append("failure")
    if cfg.on_success:
        triggers.append("success")
    cmd_str = " ".join(cfg.command) if cfg.command else "<none>"
    return (
        f"ripple: enabled, triggers={triggers}, "
        f"command={cmd_str!r}, timeout={cfg.timeout}s"
    )
