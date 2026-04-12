"""scoreboard.py – tracks per-key success/failure ratios over a sliding window.

Useful for dashboarding which commands are flakiest across retryctl runs.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass
class ScoreboardConfig:
    enabled: bool = False
    file: str = "/tmp/retryctl_scoreboard.json"
    window_seconds: int = 3600  # 1 hour rolling window

    @staticmethod
    def from_dict(raw: dict) -> "ScoreboardConfig":
        if not isinstance(raw, dict):
            raise TypeError(f"scoreboard config must be a dict, got {type(raw).__name__}")
        window = int(raw.get("window_seconds", 3600))
        if window <= 0:
            raise ValueError("window_seconds must be positive")
        return ScoreboardConfig(
            enabled=bool(raw.get("enabled", False)),
            file=str(raw.get("file", "/tmp/retryctl_scoreboard.json")),
            window_seconds=window,
        )


@dataclass
class ScoreEntry:
    key: str
    ts: float
    succeeded: bool


@dataclass
class ScoreboardTracker:
    config: ScoreboardConfig
    _entries: List[ScoreEntry] = field(default_factory=list)

    def record(self, key: str, succeeded: bool) -> None:
        if not self.config.enabled:
            return
        self._entries.append(ScoreEntry(key=key, ts=time.time(), succeeded=succeeded))
        self._persist()

    def summary(self, key: Optional[str] = None) -> dict:
        """Return {key: {attempts, successes, failures, ratio}} for the window."""
        cutoff = time.time() - self.config.window_seconds
        rows = [e for e in self._entries if e.ts >= cutoff]
        if key is not None:
            rows = [e for e in rows if e.key == key]
        result: dict = {}
        for e in rows:
            bucket = result.setdefault(e.key, {"attempts": 0, "successes": 0, "failures": 0})
            bucket["attempts"] += 1
            if e.succeeded:
                bucket["successes"] += 1
            else:
                bucket["failures"] += 1
        for v in result.values():
            v["ratio"] = round(v["successes"] / v["attempts"], 4) if v["attempts"] else 0.0
        return result

    def _persist(self) -> None:
        cutoff = time.time() - self.config.window_seconds
        self._entries = [e for e in self._entries if e.ts >= cutoff]
        path = Path(self.config.file)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = [{"key": e.key, "ts": e.ts, "succeeded": e.succeeded} for e in self._entries]
        path.write_text(json.dumps(data, indent=2))

    @classmethod
    def load(cls, config: ScoreboardConfig) -> "ScoreboardTracker":
        tracker = cls(config=config)
        path = Path(config.file)
        if not path.exists():
            return tracker
        try:
            raw = json.loads(path.read_text())
            cutoff = time.time() - config.window_seconds
            tracker._entries = [
                ScoreEntry(key=r["key"], ts=r["ts"], succeeded=r["succeeded"])
                for r in raw
                if r.get("ts", 0) >= cutoff
            ]
        except Exception:
            pass
        return tracker
