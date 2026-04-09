"""Checkpoint support: persist and restore attempt progress across process restarts."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class CheckpointConfig:
    enabled: bool = False
    directory: str = "/tmp/retryctl/checkpoints"
    ttl_seconds: int = 3600  # discard stale checkpoints after 1 hour

    @classmethod
    def from_dict(cls, data: dict) -> "CheckpointConfig":
        return cls(
            enabled=bool(data.get("enabled", False)),
            directory=str(data.get("directory", "/tmp/retryctl/checkpoints")),
            ttl_seconds=int(data.get("ttl_seconds", 3600)),
        )


@dataclass
class CheckpointData:
    command: str
    attempt: int
    started_at: float = field(default_factory=time.time)
    last_exit_code: Optional[int] = None

    def to_dict(self) -> dict:
        return {
            "command": self.command,
            "attempt": self.attempt,
            "started_at": self.started_at,
            "last_exit_code": self.last_exit_code,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CheckpointData":
        return cls(
            command=data["command"],
            attempt=int(data["attempt"]),
            started_at=float(data.get("started_at", 0.0)),
            last_exit_code=data.get("last_exit_code"),
        )


def _checkpoint_path(cfg: CheckpointConfig, command: str) -> Path:
    safe = "".join(c if c.isalnum() else "_" for c in command)[:64]
    return Path(cfg.directory) / f"{safe}.json"


def save_checkpoint(cfg: CheckpointConfig, data: CheckpointData) -> None:
    if not cfg.enabled:
        return
    path = _checkpoint_path(cfg, data.command)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data.to_dict()), encoding="utf-8")


def load_checkpoint(cfg: CheckpointConfig, command: str) -> Optional[CheckpointData]:
    if not cfg.enabled:
        return None
    path = _checkpoint_path(cfg, command)
    if not path.exists():
        return None
    raw = json.loads(path.read_text(encoding="utf-8"))
    data = CheckpointData.from_dict(raw)
    age = time.time() - data.started_at
    if age > cfg.ttl_seconds:
        path.unlink(missing_ok=True)
        return None
    return data


def clear_checkpoint(cfg: CheckpointConfig, command: str) -> None:
    if not cfg.enabled:
        return
    path = _checkpoint_path(cfg, command)
    path.unlink(missing_ok=True)
