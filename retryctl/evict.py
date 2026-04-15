"""evict.py – cache-eviction guard for retryctl.

Prevents retrying a command that has already succeeded within a
configurable TTL window, using a lightweight file-backed cache.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

_DEFAULT_LOCK_DIR = "/tmp/retryctl/evict"
_MAX_KEY_LEN = 64


@dataclass
class EvictConfig:
    enabled: bool = False
    ttl_seconds: float = 300.0
    key: Optional[str] = None
    cache_dir: str = _DEFAULT_LOCK_DIR

    @classmethod
    def from_dict(cls, raw: dict) -> "EvictConfig":
        if not isinstance(raw, dict):
            raise TypeError(f"evict config must be a dict, got {type(raw).__name__}")
        ttl = float(raw.get("ttl_seconds", 300.0))
        if ttl <= 0:
            raise ValueError("evict.ttl_seconds must be positive")
        enabled = bool(raw.get("enabled", False))
        key = raw.get("key") or None
        if key is not None:
            key = str(key)
        cache_dir = str(raw.get("cache_dir", _DEFAULT_LOCK_DIR))
        # auto-enable when a key is explicitly provided
        if key and not raw.get("enabled", False):
            enabled = True
        return cls(enabled=enabled, ttl_seconds=ttl, key=key, cache_dir=cache_dir)


class EvictBlocked(Exception):
    def __init__(self, key: str, expires_in: float) -> None:
        self.key = key
        self.expires_in = expires_in
        super().__init__(
            f"evict: key '{key}' is cached; skipping for {expires_in:.1f}s more"
        )


def _sanitise_key(key: str) -> str:
    sanitised = re.sub(r"[^a-zA-Z0-9_\-]", "_", key)
    if len(sanitised) > _MAX_KEY_LEN:
        digest = hashlib.sha1(sanitised.encode()).hexdigest()[:8]
        sanitised = sanitised[: _MAX_KEY_LEN - 9] + "_" + digest
    return sanitised


def _cache_path(cfg: EvictConfig, key: str) -> Path:
    return Path(cfg.cache_dir) / (_sanitise_key(key) + ".json")


def check_evict_gate(cfg: EvictConfig, key: str) -> None:
    """Raise EvictBlocked if a valid cache entry exists for *key*."""
    if not cfg.enabled:
        return
    path = _cache_path(cfg, key)
    if not path.exists():
        return
    try:
        data = json.loads(path.read_text())
        expires_at = float(data["expires_at"])
        remaining = expires_at - time.monotonic()
        if remaining > 0:
            raise EvictBlocked(key, remaining)
        # stale entry – remove it
        path.unlink(missing_ok=True)
    except (KeyError, ValueError, OSError) as exc:
        log.debug("evict: could not read cache entry %s: %s", path, exc)


def record_evict_success(cfg: EvictConfig, key: str) -> None:
    """Write a cache entry so subsequent runs within the TTL are skipped."""
    if not cfg.enabled:
        return
    path = _cache_path(cfg, key)
    path.parent.mkdir(parents=True, exist_ok=True)
    expires_at = time.monotonic() + cfg.ttl_seconds
    try:
        path.write_text(json.dumps({"key": key, "expires_at": expires_at}))
        log.debug("evict: cached key '%s' for %.1fs", key, cfg.ttl_seconds)
    except OSError as exc:
        log.warning("evict: could not write cache entry %s: %s", path, exc)
