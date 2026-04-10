"""Integrate WatchConfig into the top-level RetryCtlConfig dict."""
from __future__ import annotations

from retryctl.watch import WatchConfig


def parse_watch(raw: dict) -> WatchConfig:
    """Extract and parse the ``[watch]`` section from a raw config dict."""
    section = raw.get("watch", {})
    if not isinstance(section, dict):
        raise TypeError(f"[watch] must be a table, got {type(section).__name__}")
    return WatchConfig.from_dict(section)


def watch_config_to_dict(cfg: WatchConfig) -> dict:
    """Serialise a WatchConfig back to a plain dict (useful for audit/debug)."""
    return {
        "enabled": cfg.enabled,
        "paths": list(cfg.paths),
        "poll_interval": cfg.poll_interval,
        "debounce": cfg.debounce,
        "max_triggers": cfg.max_triggers,
    }
