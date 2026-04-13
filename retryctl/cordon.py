"""cordon.py — temporarily block retries for a command key after repeated failures.

A cordon is placed when failures exceed a threshold within a window. Once
cordoned, all attempts are blocked until the cordon expires.
"""
from __future__ import annotations

import time
import json
import hashlib
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass
class CordonConfig:
    enabled: bool = False
    threshold: int = 5          # failures before cordon is placed
    window_seconds: float = 60.0  # rolling window to count failures
    duration_seconds: float = 300.0  # how long the cordon lasts
    key: Optional[str] = None
    lock_dir: str = tempfile.gettempdir()

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "CordonConfig":
        if not isinstance(data, dict):
            raise TypeError("cordon config must be a mapping")
        threshold = int(data.get("threshold", 5))
        window = float(data.get("window_seconds", 60.0))
        duration = float(data.get("duration_seconds", 300.0))
        if threshold < 1:
            raise ValueError("threshold must be >= 1")
        if window <= 0:
            raise ValueError("window_seconds must be positive")
        if duration <= 0:
            raise ValueError("duration_seconds must be positive")
        enabled = bool(data.get("enabled", bool(data.get("threshold"))))
        return CordonConfig(
            enabled=enabled,
            threshold=threshold,
            window_seconds=window,
            duration_seconds=duration,
            key=data.get("key") or None,
            lock_dir=data.get("lock_dir", tempfile.gettempdir()),
        )


class CordonBlocked(Exception):
    def __init__(self, key: str, expires_at: float) -> None:
        self.key = key
        self.expires_at = expires_at
        remaining = max(0.0, expires_at - time.monotonic())
        super().__init__(
            f"cordon active for '{key}'; clears in {remaining:.1f}s"
        )


def _sanitise_key(key: str) -> str:
    return key.replace(" ", "_")[:64]


def _state_path(cfg: CordonConfig, key: str) -> Path:
    safe = _sanitise_key(key)
    digest = hashlib.sha1(safe.encode()).hexdigest()[:12]
    return Path(cfg.lock_dir) / f".cordon_{digest}.json"


@dataclass
class _CordonState:
    failure_times: list = field(default_factory=list)
    cordoned_until: float = 0.0


def _load_state(path: Path) -> _CordonState:
    if not path.exists():
        return _CordonState()
    try:
        raw = json.loads(path.read_text())
        return _CordonState(
            failure_times=raw.get("failure_times", []),
            cordoned_until=float(raw.get("cordoned_until", 0.0)),
        )
    except Exception:
        return _CordonState()


def _save_state(path: Path, state: _CordonState) -> None:
    path.write_text(json.dumps({
        "failure_times": state.failure_times,
        "cordoned_until": state.cordoned_until,
    }))


def check_cordon(cfg: CordonConfig, key: str) -> None:
    """Raise CordonBlocked if a cordon is currently active for key."""
    if not cfg.enabled:
        return
    path = _state_path(cfg, key)
    state = _load_state(path)
    now = time.monotonic()
    if state.cordoned_until > now:
        raise CordonBlocked(key, state.cordoned_until)


def record_cordon_failure(cfg: CordonConfig, key: str) -> None:
    """Record a failure; place a cordon if threshold is reached."""
    if not cfg.enabled:
        return
    path = _state_path(cfg, key)
    state = _load_state(path)
    now = time.monotonic()
    cutoff = now - cfg.window_seconds
    state.failure_times = [t for t in state.failure_times if t >= cutoff]
    state.failure_times.append(now)
    if len(state.failure_times) >= cfg.threshold:
        state.cordoned_until = now + cfg.duration_seconds
        state.failure_times = []
    _save_state(path, state)


def reset_cordon(cfg: CordonConfig, key: str) -> None:
    """Clear cordon state on success."""
    if not cfg.enabled:
        return
    path = _state_path(cfg, key)
    if path.exists():
        path.unlink(missing_ok=True)
