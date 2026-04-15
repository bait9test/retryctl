"""evict_middleware.py – wiring helpers for the eviction guard."""
from __future__ import annotations

import logging
from typing import Any

from retryctl.evict import EvictConfig, check_evict_gate, record_evict_success

log = logging.getLogger(__name__)


def parse_evict(raw_config: dict) -> EvictConfig:
    """Extract and validate the [evict] section from the top-level config dict."""
    section = raw_config.get("evict", {})
    if not isinstance(section, dict):
        raise TypeError(
            f"[evict] config section must be a table, got {type(section).__name__}"
        )
    return EvictConfig.from_dict(section)


def evict_config_to_dict(cfg: EvictConfig) -> dict[str, Any]:
    return {
        "enabled": cfg.enabled,
        "ttl_seconds": cfg.ttl_seconds,
        "key": cfg.key,
        "cache_dir": cfg.cache_dir,
    }


def resolve_key(cfg: EvictConfig, command: str) -> str:
    """Return the cache key to use, falling back to a hash of the command."""
    if cfg.key:
        return cfg.key
    import hashlib
    return "cmd_" + hashlib.sha1(command.encode()).hexdigest()[:16]


def before_run(cfg: EvictConfig, command: str) -> None:
    """Call before executing the command. Raises EvictBlocked when cached."""
    if not cfg.enabled:
        return
    key = resolve_key(cfg, command)
    check_evict_gate(cfg, key)


def on_run_success(cfg: EvictConfig, command: str) -> None:
    """Call after a successful run to populate the eviction cache."""
    if not cfg.enabled:
        return
    key = resolve_key(cfg, command)
    record_evict_success(cfg, key)


def describe_evict(cfg: EvictConfig) -> str:
    if not cfg.enabled:
        return "evict: disabled"
    return (
        f"evict: enabled | ttl={cfg.ttl_seconds}s"
        + (f" | key={cfg.key}" if cfg.key else " | key=<command-hash>")
    )
