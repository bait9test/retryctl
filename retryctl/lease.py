"""Lease-based execution guard: ensures a command holds a time-bounded lease
before running, preventing concurrent or overlapping executions across processes."""

from __future__ import annotations

import os
import time
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

log = logging.getLogger(__name__)

_DEFAULT_LEASE_DIR = "/tmp/retryctl/leases"
_DEFAULT_TTL = 60  # seconds


@dataclass
class LeaseConfig:
    enabled: bool = False
    ttl_seconds: int = _DEFAULT_TTL
    key: str = ""
    lease_dir: str = _DEFAULT_LEASE_DIR

    @staticmethod
    def from_dict(data: dict) -> "LeaseConfig":
        if not isinstance(data, dict):
            raise TypeError(f"lease config must be a dict, got {type(data).__name__}")
        ttl = int(data.get("ttl_seconds", _DEFAULT_TTL))
        if ttl <= 0:
            raise ValueError("lease ttl_seconds must be positive")
        key = str(data.get("key", ""))
        enabled = bool(data.get("enabled", bool(key)))
        return LeaseConfig(
            enabled=enabled,
            ttl_seconds=ttl,
            key=key,
            lease_dir=str(data.get("lease_dir", _DEFAULT_LEASE_DIR)),
        )


class LeaseHeld(Exception):
    def __init__(self, key: str, expires_at: float):
        self.key = key
        self.expires_at = expires_at
        remaining = max(0.0, expires_at - time.time())
        super().__init__(f"lease '{key}' is held by another process ({remaining:.1f}s remaining)")


def _sanitise_key(key: str) -> str:
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in key)[:64]


def _lease_path(cfg: LeaseConfig) -> Path:
    key = _sanitise_key(cfg.key) if cfg.key else "default"
    return Path(cfg.lease_dir) / f"{key}.lease"


def acquire_lease(cfg: LeaseConfig, pid: int | None = None) -> Path:
    """Acquire a lease file. Raises LeaseHeld if a valid lease already exists."""
    path = _lease_path(cfg)
    path.parent.mkdir(parents=True, exist_ok=True)
    now = time.time()
    if path.exists():
        try:
            data = json.loads(path.read_text())
            expires_at = float(data.get("expires_at", 0))
            if expires_at > now:
                raise LeaseHeld(cfg.key, expires_at)
            log.debug("lease '%s' expired, reclaiming", cfg.key)
        except (json.JSONDecodeError, KeyError):
            log.debug("corrupt lease file, overwriting: %s", path)
    expires_at = now + cfg.ttl_seconds
    path.write_text(json.dumps({"pid": pid or os.getpid(), "expires_at": expires_at}))
    log.debug("acquired lease '%s' until %.0f", cfg.key, expires_at)
    return path


def release_lease(path: Path) -> None:
    """Release (delete) a lease file."""
    try:
        path.unlink(missing_ok=True)
        log.debug("released lease %s", path)
    except OSError as exc:
        log.warning("failed to release lease %s: %s", path, exc)
