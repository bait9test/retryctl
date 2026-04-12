"""Stagger: introduce a per-attempt startup delay spread across parallel workers.

When multiple retryctl processes run the same command simultaneously (e.g. from
cron on many hosts), staggering prevents a thundering-herd problem by sleeping
a fraction of a base interval proportional to a worker index.
"""
from __future__ import annotations

import time
import logging
from dataclasses import dataclass, field
from typing import Any

log = logging.getLogger(__name__)


@dataclass
class StaggerConfig:
    enabled: bool = False
    # Base interval in seconds; each worker sleeps (index / total) * interval_seconds
    interval_seconds: float = 0.0
    # Worker index (0-based)
    worker_index: int = 0
    # Total number of workers
    total_workers: int = 1

    def __post_init__(self) -> None:
        if self.interval_seconds < 0:
            raise ValueError("stagger interval_seconds must be >= 0")
        if self.total_workers < 1:
            raise ValueError("stagger total_workers must be >= 1")
        if self.worker_index < 0:
            raise ValueError("stagger worker_index must be >= 0")
        if self.worker_index >= self.total_workers:
            raise ValueError("stagger worker_index must be < total_workers")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "StaggerConfig":
        if not isinstance(data, dict):
            raise TypeError("stagger config must be a mapping")
        interval = float(data.get("interval_seconds", 0.0))
        index = int(data.get("worker_index", 0))
        total = int(data.get("total_workers", 1))
        enabled = bool(data.get("enabled", interval > 0))
        return cls(
            enabled=enabled,
            interval_seconds=interval,
            worker_index=index,
            total_workers=total,
        )


class StaggerBlocked(Exception):
    """Raised if stagger is mis-configured in a way that prevents execution."""


def compute_stagger_delay(cfg: StaggerConfig) -> float:
    """Return the sleep duration in seconds for this worker."""
    if not cfg.enabled or cfg.interval_seconds == 0.0:
        return 0.0
    fraction = cfg.worker_index / cfg.total_workers
    return fraction * cfg.interval_seconds


def apply_stagger(cfg: StaggerConfig) -> float:
    """Sleep the computed stagger delay and return how long we slept."""
    delay = compute_stagger_delay(cfg)
    if delay > 0:
        log.debug(
            "stagger: worker %d/%d sleeping %.3fs",
            cfg.worker_index,
            cfg.total_workers,
            delay,
        )
        time.sleep(delay)
    return delay
