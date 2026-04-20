"""Timestamp stamping for retry attempts.

Records wall-clock and monotonic timestamps at the start of each attempt
so downstream reporters can show per-attempt timing without relying on
the metrics layer alone.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class StampConfig:
    enabled: bool = False
    include_monotonic: bool = False

    @classmethod
    def from_dict(cls, raw: dict) -> "StampConfig":
        if not isinstance(raw, dict):
            raise TypeError(f"stamp config must be a dict, got {type(raw).__name__}")
        enabled = bool(raw.get("enabled", False))
        include_monotonic = bool(raw.get("include_monotonic", False))
        return cls(enabled=enabled, include_monotonic=include_monotonic)


@dataclass
class AttemptStamp:
    attempt: int
    wall: float  # time.time()
    monotonic: Optional[float] = None  # time.monotonic() when include_monotonic=True

    def to_dict(self) -> Dict:
        d: Dict = {"attempt": self.attempt, "wall": self.wall}
        if self.monotonic is not None:
            d["monotonic"] = self.monotonic
        return d


@dataclass
class StampTracker:
    config: StampConfig
    _stamps: List[AttemptStamp] = field(default_factory=list)

    def record(self, attempt: int) -> Optional[AttemptStamp]:
        """Record a stamp for the given attempt number. Returns None if disabled."""
        if not self.config.enabled:
            return None
        mono = time.monotonic() if self.config.include_monotonic else None
        stamp = AttemptStamp(attempt=attempt, wall=time.time(), monotonic=mono)
        self._stamps.append(stamp)
        return stamp

    @property
    def stamps(self) -> List[AttemptStamp]:
        return list(self._stamps)

    def get(self, attempt: int) -> Optional[AttemptStamp]:
        for s in self._stamps:
            if s.attempt == attempt:
                return s
        return None

    def to_list(self) -> List[Dict]:
        return [s.to_dict() for s in self._stamps]

    def elapsed(self, from_attempt: int = 1) -> Optional[float]:
        """Return wall-clock seconds elapsed between the first recorded stamp
        for *from_attempt* and the most recent stamp.

        Returns None if there are fewer than two stamps or if *from_attempt*
        is not found.
        """
        if len(self._stamps) < 2:
            return None
        start = self.get(from_attempt)
        if start is None:
            return None
        return self._stamps[-1].wall - start.wall
