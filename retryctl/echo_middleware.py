"""Echo middleware helpers — integrate EchoConfig into the retry pipeline."""
from __future__ import annotations

import logging
from typing import Optional

from retryctl.echo import EchoConfig, EchoCacheEntry, load_echo_cache, save_echo_cache

log = logging.getLogger(__name__)


def parse_echo(config: dict) -> EchoConfig:
    """Extract [echo] section from a raw config dict."""
    section = config.get("echo", {})
    if not isinstance(section, dict):
        raise TypeError(f"[echo] must be a table, got {type(section).__name__}")
    cfg = EchoConfig.from_dict(section)
    # auto-enable when cache_dir is explicitly set
    if "cache_dir" in section and not section.get("enabled", False):
        cfg.enabled = True
    return cfg


def echo_config_to_dict(cfg: EchoConfig) -> dict:
    return {
        "enabled": cfg.enabled,
        "ttl_seconds": cfg.ttl_seconds,
        "cache_dir": cfg.cache_dir,
        "warn_on_echo": cfg.warn_on_echo,
    }


def on_run_success(cfg: EchoConfig, key: str, stdout: str, stderr: str) -> None:
    """Persist a successful run's output to the echo cache."""
    if not cfg.enabled:
        return
    save_echo_cache(cfg, key, stdout, stderr)


def maybe_echo(cfg: EchoConfig, key: str) -> Optional[EchoCacheEntry]:
    """Return cached output if available and the config is enabled."""
    if not cfg.enabled:
        return None
    entry = load_echo_cache(cfg, key)
    if entry is None:
        return None
    if cfg.warn_on_echo:
        log.warning("echo: returning cached output for key %r (live command failed)", key)
    return entry


def describe_echo(cfg: EchoConfig) -> str:
    if not cfg.enabled:
        return "echo disabled"
    return f"echo enabled (ttl={cfg.ttl_seconds}s, dir={cfg.cache_dir})"
