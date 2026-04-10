"""File-watch trigger: re-run the command when watched paths change."""
from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class WatchConfig:
    enabled: bool = False
    paths: List[str] = field(default_factory=list)
    poll_interval: float = 1.0          # seconds between stat checks
    debounce: float = 0.2               # seconds to wait after last change
    max_triggers: Optional[int] = None  # None = unlimited

    @staticmethod
    def from_dict(data: dict) -> "WatchConfig":
        return WatchConfig(
            enabled=bool(data.get("enabled", False)),
            paths=[str(p) for p in data.get("paths", [])],
            poll_interval=float(data.get("poll_interval", 1.0)),
            debounce=float(data.get("debounce", 0.2)),
            max_triggers=(
                int(data["max_triggers"]) if data.get("max_triggers") is not None else None
            ),
        )


def _snapshot(paths: List[str]) -> Dict[str, float]:
    """Return a mapping of path -> mtime (0.0 if missing)."""
    result: Dict[str, float] = {}
    for p in paths:
        try:
            result[p] = Path(p).stat().st_mtime
        except FileNotFoundError:
            result[p] = 0.0
    return result


def _changed(old: Dict[str, float], new: Dict[str, float]) -> List[str]:
    return [p for p, mtime in new.items() if mtime != old.get(p, mtime)]


def watch_for_change(
    cfg: WatchConfig,
    *,
    _sleep: object = time.sleep,  # injectable for tests
) -> List[str]:
    """Block until at least one watched path changes; return list of changed paths."""
    if not cfg.paths:
        raise ValueError("WatchConfig.paths must not be empty")

    sleep = _sleep  # type: ignore[assignment]
    baseline = _snapshot(cfg.paths)

    while True:
        sleep(cfg.poll_interval)
        current = _snapshot(cfg.paths)
        changed = _changed(baseline, current)
        if changed:
            # debounce: wait a bit then re-snapshot
            sleep(cfg.debounce)
            final = _snapshot(cfg.paths)
            baseline = final
            return _changed(current, final) or changed
