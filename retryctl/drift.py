"""Drift detection: warn when actual retry delay deviates significantly from expected."""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class DriftConfig:
    enabled: bool = False
    # Warn when actual sleep exceeds expected by more than this fraction (0.2 = 20%)
    warn_threshold: float = 0.2
    # Abort (raise) when drift exceeds this fraction; None means never abort
    abort_threshold: Optional[float] = None

    @staticmethod
    def from_dict(data: dict) -> "DriftConfig":
        if not isinstance(data, dict):
            raise TypeError(f"DriftConfig expects a dict, got {type(data).__name__}")
        warn = float(data.get("warn_threshold", 0.2))
        if warn < 0:
            raise ValueError("warn_threshold must be >= 0")
        abort_raw = data.get("abort_threshold")
        abort: Optional[float] = None
        if abort_raw is not None:
            abort = float(abort_raw)
            if abort < 0:
                raise ValueError("abort_threshold must be >= 0")
        return DriftConfig(
            enabled=bool(data.get("enabled", False)),
            warn_threshold=warn,
            abort_threshold=abort,
        )


class DriftExceeded(RuntimeError):
    """Raised when actual sleep drift exceeds the abort threshold."""

    def __init__(self, expected: float, actual: float, threshold: float) -> None:
        self.expected = expected
        self.actual = actual
        self.threshold = threshold
        super().__init__(
            f"Drift abort: expected {expected:.3f}s sleep, actual {actual:.3f}s "
            f"(drift {_pct(expected, actual):.1f}% > abort threshold {threshold * 100:.1f}%)"
        )


def _pct(expected: float, actual: float) -> float:
    if expected == 0:
        return 0.0
    return ((actual - expected) / expected) * 100


def sleep_with_drift_check(expected_seconds: float, cfg: DriftConfig) -> float:
    """Sleep for *expected_seconds* and check for drift.

    Returns the actual elapsed time.
    Logs a warning if drift exceeds warn_threshold.
    Raises DriftExceeded if drift exceeds abort_threshold.
    """
    start = time.monotonic()
    time.sleep(expected_seconds)
    actual = time.monotonic() - start

    if not cfg.enabled or expected_seconds <= 0:
        return actual

    fraction = (actual - expected_seconds) / expected_seconds if expected_seconds else 0.0

    if cfg.abort_threshold is not None and fraction > cfg.abort_threshold:
        raise DriftExceeded(expected_seconds, actual, cfg.abort_threshold)

    if fraction > cfg.warn_threshold:
        logger.warning(
            "Retry delay drift detected: expected %.3fs, actual %.3fs (%.1f%% over threshold %.1f%%)",
            expected_seconds,
            actual,
            fraction * 100,
            cfg.warn_threshold * 100,
        )

    return actual
