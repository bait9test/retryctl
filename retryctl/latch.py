"""Latch: hold a 'tripped' flag in a temp file so that once a run
fails a minimum number of times the latch is considered *set* and
subsequent runs are blocked until it is manually cleared.
"""
from __future__ import annotations

import json
import logging
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

_DEFAULT_LOCK_DIR = Path(tempfile.gettempdir()) / "retryctl" / "latches"


@dataclass
class LatchConfig:
    enabled: bool = False
    threshold: int = 3          # consecutive failures before latch trips
    key: str = "default"
    lock_dir: Path = field(default_factory=lambda: _DEFAULT_LOCK_DIR)

    @staticmethod
    def from_dict(data: dict) -> "LatchConfig":
        if not isinstance(data, dict):
            raise TypeError("latch config must be a mapping")
        threshold = int(data.get("threshold", 3))
        if threshold < 1:
            raise ValueError("latch threshold must be >= 1")
        key = str(data.get("key", "default")).strip() or "default"
        lock_dir = Path(data.get("lock_dir", _DEFAULT_LOCK_DIR))
        enabled = bool(data.get("enabled", False)) or "threshold" in data
        return LatchConfig(enabled=enabled, threshold=threshold, key=key, lock_dir=lock_dir)


class LatchTripped(Exception):
    def __init__(self, key: str, failures: int) -> None:
        self.key = key
        self.failures = failures
        super().__init__(f"latch '{key}' is tripped after {failures} consecutive failure(s)")


def _sanitise_key(key: str) -> str:
    sanitised = "".join(c if c.isalnum() or c in "-_." else "_" for c in key)
    return sanitised[:64]


def _latch_path(cfg: LatchConfig) -> Path:
    cfg.lock_dir.mkdir(parents=True, exist_ok=True)
    return cfg.lock_dir / f"{_sanitise_key(cfg.key)}.latch.json"


def _read_failures(path: Path) -> int:
    try:
        data = json.loads(path.read_text())
        return int(data.get("failures", 0))
    except (FileNotFoundError, json.JSONDecodeError, ValueError):
        return 0


def _write_failures(path: Path, count: int) -> None:
    path.write_text(json.dumps({"failures": count}))


def check_latch(cfg: LatchConfig) -> None:
    """Raise LatchTripped if the latch is already set."""
    if not cfg.enabled:
        return
    path = _latch_path(cfg)
    failures = _read_failures(path)
    if failures >= cfg.threshold:
        raise LatchTripped(cfg.key, failures)


def on_attempt_failure(cfg: LatchConfig) -> None:
    """Increment the consecutive-failure counter; trip latch if threshold reached."""
    if not cfg.enabled:
        return
    path = _latch_path(cfg)
    count = _read_failures(path) + 1
    _write_failures(path, count)
    if count >= cfg.threshold:
        log.warning("latch '%s' tripped after %d consecutive failure(s)", cfg.key, count)


def reset_latch(cfg: LatchConfig) -> None:
    """Clear the latch (called on success or manual reset)."""
    if not cfg.enabled:
        return
    path = _latch_path(cfg)
    try:
        path.unlink()
    except FileNotFoundError:
        pass
    log.debug("latch '%s' reset", cfg.key)
