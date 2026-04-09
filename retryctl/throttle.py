"""Throttle: per-command concurrency guard using a file-based lock.

Prevents multiple retryctl processes from running the same command
concurrently when `throttle.enabled` is true.
"""

from __future__ import annotations

import fcntl
import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

DEFAULT_LOCK_DIR = "/tmp/retryctl/locks"


@dataclass
class ThrottleConfig:
    enabled: bool = False
    lock_dir: str = DEFAULT_LOCK_DIR
    timeout_seconds: float = 30.0
    lock_key: Optional[str] = None  # defaults to sanitised command string


def _sanitise_key(key: str) -> str:
    """Replace non-alphanumeric characters so the key is safe as a filename."""
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in key)[:128]


def _lock_path(cfg: ThrottleConfig, command: str) -> Path:
    key = _sanitise_key(cfg.lock_key or command)
    return Path(cfg.lock_dir) / f"{key}.lock"


class ThrottleLock:
    """Context manager that acquires an exclusive file lock."""

    def __init__(self, cfg: ThrottleConfig, command: str) -> None:
        self._cfg = cfg
        self._path = _lock_path(cfg, command)
        self._fd: Optional[int] = None

    def acquire(self) -> bool:
        """Try to acquire lock within timeout. Returns True on success."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._fd = os.open(str(self._path), os.O_CREAT | os.O_WRONLY, 0o600)
        deadline = time.monotonic() + self._cfg.timeout_seconds
        while True:
            try:
                fcntl.flock(self._fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                logger.debug("throttle: lock acquired %s", self._path)
                return True
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    logger.warning("throttle: timed out waiting for lock %s", self._path)
                    os.close(self._fd)
                    self._fd = None
                    return False
                time.sleep(0.1)

    def release(self) -> None:
        if self._fd is not None:
            fcntl.flock(self._fd, fcntl.LOCK_UN)
            os.close(self._fd)
            self._fd = None
            logger.debug("throttle: lock released %s", self._path)

    def __enter__(self) -> "ThrottleLock":
        return self

    def __exit__(self, *_: object) -> None:
        self.release()
