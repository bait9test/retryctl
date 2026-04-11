"""Replay support: record and re-run the last failed command."""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import List, Optional

_DEFAULT_REPLAY_DIR = "/tmp/retryctl/replay"


@dataclass
class ReplayConfig:
    enabled: bool = False
    replay_dir: str = _DEFAULT_REPLAY_DIR

    @classmethod
    def from_dict(cls, data: dict) -> "ReplayConfig":
        if not isinstance(data, dict):
            raise TypeError("replay config must be a dict")
        return cls(
            enabled=bool(data.get("enabled", False)),
            replay_dir=str(data.get("replay_dir", _DEFAULT_REPLAY_DIR)),
        )


@dataclass
class ReplayRecord:
    command: List[str]
    exit_code: int
    timestamp: float = field(default_factory=time.time)
    attempt_count: int = 1
    label: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "ReplayRecord":
        return cls(
            command=list(data["command"]),
            exit_code=int(data["exit_code"]),
            timestamp=float(data.get("timestamp", 0.0)),
            attempt_count=int(data.get("attempt_count", 1)),
            label=data.get("label"),
        )


def _replay_file(cfg: ReplayConfig, label: Optional[str] = None) -> Path:
    key = label if label else "default"
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in key)[:64]
    return Path(cfg.replay_dir) / f"{safe}.json"


def save_replay(cfg: ReplayConfig, record: ReplayRecord) -> None:
    if not cfg.enabled:
        return
    path = _replay_file(cfg, record.label)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record.to_dict(), indent=2))


def load_replay(cfg: ReplayConfig, label: Optional[str] = None) -> Optional[ReplayRecord]:
    if not cfg.enabled:
        return None
    path = _replay_file(cfg, label)
    if not path.exists():
        return None
    data = json.loads(path.read_text())
    return ReplayRecord.from_dict(data)


def clear_replay(cfg: ReplayConfig, label: Optional[str] = None) -> None:
    path = _replay_file(cfg, label)
    if path.exists():
        path.unlink()
