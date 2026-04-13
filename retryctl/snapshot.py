"""Snapshot middleware — capture and compare command output across attempts."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class SnapshotConfig:
    enabled: bool = False
    path: str = "/tmp/retryctl_snapshots"
    compare_stdout: bool = True
    compare_stderr: bool = False
    fail_on_change: bool = False

    @staticmethod
    def from_dict(data: dict) -> "SnapshotConfig":
        if not isinstance(data, dict):
            raise TypeError("snapshot config must be a mapping")
        cfg = SnapshotConfig()
        cfg.enabled = bool(data.get("enabled", cfg.enabled))
        cfg.path = str(data.get("path", cfg.path))
        cfg.compare_stdout = bool(data.get("compare_stdout", cfg.compare_stdout))
        cfg.compare_stderr = bool(data.get("compare_stderr", cfg.compare_stderr))
        cfg.fail_on_change = bool(data.get("fail_on_change", cfg.fail_on_change))
        return cfg


@dataclass
class SnapshotEntry:
    attempt: int
    stdout_hash: Optional[str]
    stderr_hash: Optional[str]
    changed: bool = False

    def to_dict(self) -> dict:
        return {
            "attempt": self.attempt,
            "stdout_hash": self.stdout_hash,
            "stderr_hash": self.stderr_hash,
            "changed": self.changed,
        }


def _hash(text: Optional[str]) -> Optional[str]:
    if text is None:
        return None
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def take_snapshot(cfg: SnapshotConfig, attempt: int, stdout: Optional[str], stderr: Optional[str]) -> SnapshotEntry:
    sh = _hash(stdout) if cfg.compare_stdout else None
    eh = _hash(stderr) if cfg.compare_stderr else None
    return SnapshotEntry(attempt=attempt, stdout_hash=sh, stderr_hash=eh)


def compare_snapshots(prev: SnapshotEntry, curr: SnapshotEntry) -> bool:
    """Return True if output changed between attempts."""
    return prev.stdout_hash != curr.stdout_hash or prev.stderr_hash != curr.stderr_hash


def save_snapshots(cfg: SnapshotConfig, key: str, entries: list[SnapshotEntry]) -> None:
    dest = Path(cfg.path)
    dest.mkdir(parents=True, exist_ok=True)
    safe_key = key.replace("/", "_").replace(" ", "_")[:64]
    out = dest / f"{safe_key}.json"
    out.write_text(json.dumps([e.to_dict() for e in entries], indent=2))


def load_snapshots(cfg: SnapshotConfig, key: str) -> list[SnapshotEntry]:
    dest = Path(cfg.path)
    safe_key = key.replace("/", "_").replace(" ", "_")[:64]
    src = dest / f"{safe_key}.json"
    if not src.exists():
        return []
    try:
        raw = json.loads(src.read_text())
    except (json.JSONDecodeError, OSError) as exc:
        raise RuntimeError(f"failed to load snapshots from {src}: {exc}") from exc
    if not isinstance(raw, list):
        raise RuntimeError(f"unexpected snapshot format in {src}: expected a list")
    return [SnapshotEntry(**r) for r in raw]
