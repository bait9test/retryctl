"""Echo middleware — replay the last successful output when a command fails.

If enabled and a previous successful output is cached, the cached output is
returned instead of propagating the failure, optionally logging a warning.
"""
from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

_DEFAULT_CACHE_DIR = "/tmp/retryctl/echo"
_DEFAULT_TTL = 3600  # seconds


@dataclass
class EchoConfig:
    enabled: bool = False
    ttl_seconds: int = _DEFAULT_TTL
    cache_dir: str = _DEFAULT_CACHE_DIR
    warn_on_echo: bool = True

    @staticmethod
    def from_dict(data: dict) -> "EchoConfig":
        if not isinstance(data, dict):
            raise TypeError(f"EchoConfig expects a dict, got {type(data).__name__}")
        ttl = int(data.get("ttl_seconds", _DEFAULT_TTL))
        if ttl < 0:
            raise ValueError("ttl_seconds must be >= 0")
        return EchoConfig(
            enabled=bool(data.get("enabled", False)),
            ttl_seconds=ttl,
            cache_dir=str(data.get("cache_dir", _DEFAULT_CACHE_DIR)),
            warn_on_echo=bool(data.get("warn_on_echo", True)),
        )


@dataclass
class EchoCacheEntry:
    stdout: str
    stderr: str
    saved_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {"stdout": self.stdout, "stderr": self.stderr, "saved_at": self.saved_at}

    @staticmethod
    def from_dict(data: dict) -> "EchoCacheEntry":
        return EchoCacheEntry(
            stdout=data["stdout"],
            stderr=data["stderr"],
            saved_at=float(data["saved_at"]),
        )


def _cache_path(cfg: EchoConfig, key: str) -> Path:
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in key)[:80]
    return Path(cfg.cache_dir) / f"{safe}.json"


def load_echo_cache(cfg: EchoConfig, key: str) -> Optional[EchoCacheEntry]:
    path = _cache_path(cfg, key)
    if not path.exists():
        return None
    try:
        entry = EchoCacheEntry.from_dict(json.loads(path.read_text()))
    except Exception:
        return None
    if cfg.ttl_seconds > 0 and (time.time() - entry.saved_at) > cfg.ttl_seconds:
        log.debug("echo: cache expired for key %r", key)
        return None
    return entry


def save_echo_cache(cfg: EchoConfig, key: str, stdout: str, stderr: str) -> None:
    path = _cache_path(cfg, key)
    os.makedirs(path.parent, exist_ok=True)
    entry = EchoCacheEntry(stdout=stdout, stderr=stderr)
    path.write_text(json.dumps(entry.to_dict()))
    log.debug("echo: cached output for key %r", key)
