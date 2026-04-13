"""roster.py – track which commands have been run and how often.

Provides a lightweight persistent counter so operators can see
which retryctl jobs are most active across invocations.
"""
from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

log = logging.getLogger(__name__)

_DEFAULT_ROSTER_FILE = os.path.expanduser("~/.retryctl/roster.json")


@dataclass
class RosterConfig:
    enabled: bool = False
    roster_file: str = _DEFAULT_ROSTER_FILE
    max_entries: int = 500

    @classmethod
    def from_dict(cls, data: dict) -> "RosterConfig":
        if not isinstance(data, dict):
            raise TypeError("roster config must be a mapping")
        enabled = bool(data.get("enabled", False))
        roster_file = str(data.get("roster_file", _DEFAULT_ROSTER_FILE))
        max_entries = int(data.get("max_entries", 500))
        if max_entries < 1:
            raise ValueError("max_entries must be >= 1")
        return cls(enabled=enabled, roster_file=roster_file, max_entries=max_entries)


@dataclass
class RosterEntry:
    command: str
    run_count: int = 0
    failure_count: int = 0
    last_seen: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "command": self.command,
            "run_count": self.run_count,
            "failure_count": self.failure_count,
            "last_seen": self.last_seen,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "RosterEntry":
        return cls(
            command=data["command"],
            run_count=int(data.get("run_count", 0)),
            failure_count=int(data.get("failure_count", 0)),
            last_seen=float(data.get("last_seen", 0.0)),
        )


def _load_roster(path: str) -> Dict[str, RosterEntry]:
    try:
        raw = Path(path).read_text()
        entries = json.loads(raw)
        return {e["command"]: RosterEntry.from_dict(e) for e in entries}
    except FileNotFoundError:
        return {}
    except Exception as exc:  # noqa: BLE001
        log.warning("roster: could not load %s: %s", path, exc)
        return {}


def _save_roster(path: str, entries: Dict[str, RosterEntry], max_entries: int) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    ordered: List[RosterEntry] = sorted(
        entries.values(), key=lambda e: e.last_seen, reverse=True
    )[:max_entries]
    try:
        Path(path).write_text(json.dumps([e.to_dict() for e in ordered], indent=2))
    except Exception as exc:  # noqa: BLE001
        log.warning("roster: could not save %s: %s", path, exc)


def record_run(
    cfg: RosterConfig,
    command: str,
    *,
    succeeded: bool,
    now: Optional[float] = None,
) -> None:
    """Increment counters for *command* in the persistent roster."""
    if not cfg.enabled:
        return
    entries = _load_roster(cfg.roster_file)
    entry = entries.get(command) or RosterEntry(command=command)
    entry.run_count += 1
    if not succeeded:
        entry.failure_count += 1
    entry.last_seen = now if now is not None else time.time()
    entries[command] = entry
    _save_roster(cfg.roster_file, entries, cfg.max_entries)


def list_entries(cfg: RosterConfig) -> List[RosterEntry]:
    """Return all roster entries sorted by last_seen descending."""
    if not cfg.enabled:
        return []
    entries = _load_roster(cfg.roster_file)
    return sorted(entries.values(), key=lambda e: e.last_seen, reverse=True)
