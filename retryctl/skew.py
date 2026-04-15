"""Skew detection: warn or abort when attempt durations diverge significantly."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List, Optional

log = logging.getLogger(__name__)


@dataclass
class SkewConfig:
    enabled: bool = False
    warn_pct: float = 50.0   # warn when latest duration deviates > N% from rolling mean
    abort_pct: float = 0.0   # 0 = disabled; abort when deviation exceeds this
    min_samples: int = 3     # need at least this many samples before evaluating

    @staticmethod
    def from_dict(raw: dict) -> "SkewConfig":
        if not isinstance(raw, dict):
            raise TypeError(f"skew config must be a dict, got {type(raw).__name__}")
        warn_pct = float(raw.get("warn_pct", 50.0))
        abort_pct = float(raw.get("abort_pct", 0.0))
        min_samples = int(raw.get("min_samples", 3))
        if warn_pct < 0:
            raise ValueError("warn_pct must be >= 0")
        if abort_pct < 0:
            raise ValueError("abort_pct must be >= 0")
        if min_samples < 1:
            raise ValueError("min_samples must be >= 1")
        enabled = bool(raw.get("enabled", warn_pct > 0 or abort_pct > 0))
        return SkewConfig(enabled=enabled, warn_pct=warn_pct,
                          abort_pct=abort_pct, min_samples=min_samples)


class SkewExceeded(Exception):
    def __init__(self, deviation_pct: float, mean: float, latest: float) -> None:
        self.deviation_pct = deviation_pct
        self.mean = mean
        self.latest = latest
        super().__init__(
            f"attempt duration skew {deviation_pct:.1f}% exceeds abort threshold "
            f"(mean={mean:.3f}s, latest={latest:.3f}s)"
        )


@dataclass
class SkewTracker:
    config: SkewConfig
    _samples: List[float] = field(default_factory=list)

    def record(self, duration_seconds: float) -> None:
        """Record a new attempt duration and check for skew."""
        if not self.config.enabled:
            return
        self._samples.append(duration_seconds)
        if len(self._samples) < self.config.min_samples:
            return
        mean = sum(self._samples[:-1]) / len(self._samples[:-1])
        if mean == 0:
            return
        deviation_pct = abs(duration_seconds - mean) / mean * 100.0
        if self.config.abort_pct > 0 and deviation_pct >= self.config.abort_pct:
            raise SkewExceeded(deviation_pct, mean, duration_seconds)
        if deviation_pct >= self.config.warn_pct:
            log.warning(
                "skew detected: attempt duration %.3fs deviates %.1f%% from mean %.3fs",
                duration_seconds, deviation_pct, mean,
            )

    @property
    def samples(self) -> List[float]:
        return list(self._samples)

    def reset(self) -> None:
        self._samples.clear()
