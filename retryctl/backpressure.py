"""Backpressure: slow down retry attempts when a load indicator is high.

Reads a numeric value from a file or command and compares it against a
configured threshold.  When the value exceeds the threshold the attempt
is delayed by an extra penalty before proceeding.
"""
from __future__ import annotations

import logging
import subprocess
import time
from dataclasses import dataclass, field
from typing import Optional

log = logging.getLogger(__name__)


@dataclass
class BackpressureConfig:
    enabled: bool = False
    # path to a file whose first line is a float (e.g. /proc/loadavg)
    source_file: Optional[str] = None
    # shell command whose stdout is a float
    source_cmd: Optional[str] = None
    threshold: float = 1.0
    # extra seconds to sleep when load > threshold
    penalty_seconds: float = 5.0
    # never sleep longer than this many seconds
    max_penalty_seconds: float = 60.0

    @classmethod
    def from_dict(cls, raw: dict) -> "BackpressureConfig":
        if not isinstance(raw, dict):
            raise TypeError("backpressure config must be a mapping")
        enabled = bool(raw.get("enabled", False))
        source_file = raw.get("source_file") or None
        source_cmd = raw.get("source_cmd") or None
        if source_file and source_cmd:
            raise ValueError("specify source_file or source_cmd, not both")
        threshold = float(raw.get("threshold", 1.0))
        penalty = float(raw.get("penalty_seconds", 5.0))
        max_penalty = float(raw.get("max_penalty_seconds", 60.0))
        if penalty < 0:
            raise ValueError("penalty_seconds must be >= 0")
        if max_penalty < penalty:
            raise ValueError("max_penalty_seconds must be >= penalty_seconds")
        # auto-enable when a source is provided
        if (source_file or source_cmd) and not raw.get("enabled"):
            enabled = True
        return cls(
            enabled=enabled,
            source_file=source_file,
            source_cmd=source_cmd,
            threshold=threshold,
            penalty_seconds=penalty,
            max_penalty_seconds=max_penalty,
        )


def _read_load(cfg: BackpressureConfig) -> Optional[float]:
    """Return the current load value or None if it cannot be determined."""
    try:
        if cfg.source_file:
            with open(cfg.source_file) as fh:
                return float(fh.readline().split()[0])
        if cfg.source_cmd:
            result = subprocess.run(
                cfg.source_cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=5,
            )
            return float(result.stdout.strip())
    except Exception as exc:  # noqa: BLE001
        log.warning("backpressure: could not read load value: %s", exc)
    return None


def apply_backpressure(cfg: BackpressureConfig, attempt: int) -> None:
    """Sleep for a penalty duration when the load exceeds the threshold."""
    if not cfg.enabled:
        return
    load = _read_load(cfg)
    if load is None:
        return
    if load <= cfg.threshold:
        log.debug("backpressure: load %.2f <= threshold %.2f, no penalty", load, cfg.threshold)
        return
    # scale penalty linearly with how far over the threshold we are
    ratio = load / max(cfg.threshold, 0.001)
    penalty = min(cfg.penalty_seconds * ratio, cfg.max_penalty_seconds)
    log.warning(
        "backpressure: load %.2f > threshold %.2f on attempt %d — sleeping %.1fs",
        load, cfg.threshold, attempt, penalty,
    )
    time.sleep(penalty)
