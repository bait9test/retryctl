"""Per-command retry quota enforcement backed by a simple file-based counter."""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class QuotaConfig:
    enabled: bool = False
    max_retries: int = 0          # 0 means unlimited
    window_seconds: int = 3600    # rolling window
    state_dir: str = "/tmp/retryctl/quota"
    key: Optional[str] = None     # defaults to sanitised command

    @staticmethod
    def from_dict(d: dict) -> "QuotaConfig":
        return QuotaConfig(
            enabled=bool(d.get("enabled", False)),
            max_retries=int(d.get("max_retries", 0)),
            window_seconds=int(d.get("window_seconds", 3600)),
            state_dir=str(d.get("state_dir", "/tmp/retryctl/quota")),
            key=d.get("key") or None,
        )


class QuotaExceeded(Exception):
    def __init__(self, used: int, limit: int, window: int):
        super().__init__(
            f"Retry quota exceeded: {used}/{limit} retries used in the last {window}s"
        )
        self.used = used
        self.limit = limit
        self.window = window


def _sanitise_key(key: str) -> str:
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in key)
    return safe[:64]


def _quota_file(cfg: QuotaConfig, command: str) -> Path:
    key = _sanitise_key(cfg.key or command)
    return Path(cfg.state_dir) / f"{key}.json"


def _load_timestamps(path: Path, window: int) -> list[float]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text())
        cutoff = time.time() - window
        return [t for t in data.get("timestamps", []) if t >= cutoff]
    except (json.JSONDecodeError, OSError):
        return []


def _save_timestamps(path: Path, timestamps: list[float]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"timestamps": timestamps}))


def check_quota(cfg: QuotaConfig, command: str) -> int:
    """Return current retry count within the window. Raises QuotaExceeded if over limit."""
    if not cfg.enabled or cfg.max_retries <= 0:
        return 0
    path = _quota_file(cfg, command)
    timestamps = _load_timestamps(path, cfg.window_seconds)
    if len(timestamps) >= cfg.max_retries:
        raise QuotaExceeded(len(timestamps), cfg.max_retries, cfg.window_seconds)
    return len(timestamps)


def record_retry(cfg: QuotaConfig, command: str) -> None:
    """Record one retry attempt against the quota."""
    if not cfg.enabled or cfg.max_retries <= 0:
        return
    path = _quota_file(cfg, command)
    timestamps = _load_timestamps(path, cfg.window_seconds)
    timestamps.append(time.time())
    _save_timestamps(path, timestamps)


def reset_quota(cfg: QuotaConfig, command: str) -> None:
    """Clear quota state for a command (e.g. on success)."""
    if not cfg.enabled:
        return
    path = _quota_file(cfg, command)
    if path.exists():
        path.unlink(missing_ok=True)
