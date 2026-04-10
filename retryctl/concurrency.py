"""Concurrency guard — prevent overlapping retryctl runs for the same command key."""

from __future__ import annotations

import fcntl
import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

_DEFAULT_LOCK_DIR = "/tmp/retryctl/locks"


@dataclass
class ConcurrencyConfig:
    enabled: bool = False
    key: Optional[str] = None
    lock_dir: str = _DEFAULT_LOCK_DIR
    wait: bool = False          # if True, block until lock is free; else fail fast
    timeout_seconds: float = 30.0

    @staticmethod
    def from_dict(data: dict) -> "ConcurrencyConfig":
        return ConcurrencyConfig(
            enabled=bool(data.get("enabled", False)),
            key=data.get("key") or None,
            lock_dir=data.get("lock_dir", _DEFAULT_LOCK_DIR),
            wait=bool(data.get("wait", False)),
            timeout_seconds=float(data.get("timeout_seconds", 30.0)),
        )


class ConcurrencyBlocked(RuntimeError):
    """Raised when another instance already holds the lock and wait=False."""


def _lock_path(cfg: ConcurrencyConfig, command_key: str) -> Path:
    safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in command_key)[:128]
    return Path(cfg.lock_dir) / f"{safe}.lock"


class ConcurrencyLock:
    """Context manager that acquires/releases a file-based concurrency lock."""

    def __init__(self, cfg: ConcurrencyConfig, command_key: str) -> None:
        self._cfg = cfg
        self._path = _lock_path(cfg, command_key)
        self._fh = None

    def acquire(self) -> None:
        os.makedirs(self._path.parent, exist_ok=True)
        self._fh = open(self._path, "w")
        flag = fcntl.LOCK_EX if self._cfg.wait else fcntl.LOCK_EX | fcntl.LOCK_NB
        deadline = time.monotonic() + self._cfg.timeout_seconds
        while True:
            try:
                fcntl.flock(self._fh, flag)
                log.debug("concurrency lock acquired: %s", self._path)
                return
            except BlockingIOError:
                if not self._cfg.wait or time.monotonic() >= deadline:
                    self._fh.close()
                    self._fh = None
                    raise ConcurrencyBlocked(
                        f"Another retryctl instance holds the lock: {self._path}"
                    )
                time.sleep(0.25)

    def release(self) -> None:
        if self._fh is not None:
            fcntl.flock(self._fh, fcntl.LOCK_UN)
            self._fh.close()
            self._fh = None
            log.debug("concurrency lock released: %s", self._path)

    def __enter__(self) -> "ConcurrencyLock":
        self.acquire()
        return self

    def __exit__(self, *_) -> None:
        self.release()
