"""Cooldown enforcement — prevents a command from running again too soon after a recent success."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import json

_DEFAULT_LOCK_DIR = "/tmp/retryctl/cooldown"


@dataclass
class CooldownConfig:
    enabled: bool = False
    seconds: float = 60.0
    key: str = ""
    lock_dir: str = _DEFAULT_LOCK_DIR

    @classmethod
    def from_dict(cls, data: dict) -> "CooldownConfig":
        seconds = float(data.get("seconds", 60.0))
        if seconds < 0:
            raise ValueError("cooldown.seconds must be non-negative")
        return cls(
            enabled=bool(data.get("enabled", False)),
            seconds=seconds,
            key=str(data.get("key", "")),
            lock_dir=str(data.get("lock_dir", _DEFAULT_LOCK_DIR)),
        )


class CooldownBlocked(Exception):
    """Raised when the cooldown period has not yet elapsed."""

    def __init__(self, remaining: float) -> None:
        self.remaining = remaining
        super().__init__(f"Cooldown active: {remaining:.1f}s remaining")


def _sanitise_key(key: str) -> str:
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in key)
    return safe[:64] or "default"


def _state_path(cfg: CooldownConfig, command_key: str) -> Path:
    key = cfg.key or command_key
    filename = _sanitise_key(key) + ".json"
    return Path(cfg.lock_dir) / filename


def record_success(cfg: CooldownConfig, command_key: str) -> None:
    """Persist the current timestamp as the last successful run."""
    if not cfg.enabled:
        return
    path = _state_path(cfg, command_key)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"last_success": time.time()}))


def check_cooldown(cfg: CooldownConfig, command_key: str) -> None:
    """Raise CooldownBlocked if within the cooldown window."""
    if not cfg.enabled:
        return
    path = _state_path(cfg, command_key)
    if not path.exists():
        return
    try:
        data = json.loads(path.read_text())
        last = float(data.get("last_success", 0))
    except (ValueError, KeyError, OSError):
        return
    elapsed = time.time() - last
    if elapsed < cfg.seconds:
        raise CooldownBlocked(cfg.seconds - elapsed)


def clear_cooldown(cfg: CooldownConfig, command_key: str) -> None:
    """Remove the cooldown state file."""
    path = _state_path(cfg, command_key)
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass
