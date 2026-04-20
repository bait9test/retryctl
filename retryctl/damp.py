"""damp.py – Damping suppresses repeated identical failures within a window.

If the same exit-code + stderr-fingerprint pair is seen more than
`threshold` times inside `window_seconds`, further attempts are
damped (skipped / short-circuited) until the window rolls over.
"""
from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class DampConfig:
    enabled: bool = False
    threshold: int = 3          # identical failures before damping kicks in
    window_seconds: float = 60.0
    fingerprint_stderr: bool = True  # include stderr in fingerprint

    def __post_init__(self) -> None:
        if self.threshold < 1:
            raise ValueError("damp.threshold must be >= 1")
        if self.window_seconds <= 0:
            raise ValueError("damp.window_seconds must be > 0")

    @classmethod
    def from_dict(cls, raw: object) -> "DampConfig":
        if not isinstance(raw, dict):
            raise TypeError(f"[damp] config must be a dict, got {type(raw).__name__}")
        enabled: bool = bool(raw.get("enabled", False))
        threshold = int(raw.get("threshold", 3))
        window = float(raw.get("window_seconds", 60.0))
        fp_stderr = bool(raw.get("fingerprint_stderr", True))
        cfg = cls(
            enabled=enabled,
            threshold=threshold,
            window_seconds=window,
            fingerprint_stderr=fp_stderr,
        )
        # auto-enable when threshold explicitly supplied
        if "threshold" in raw and not raw.get("enabled", False):
            cfg.enabled = True
        return cfg


class DampedAttempt(Exception):
    """Raised when an attempt is suppressed by the damping logic."""

    def __init__(self, fingerprint: str, count: int) -> None:
        self.fingerprint = fingerprint
        self.count = count
        super().__init__(
            f"attempt damped – fingerprint '{fingerprint}' seen {count}x in window"
        )


@dataclass
class _Bucket:
    timestamps: List[float] = field(default_factory=list)


class DampTracker:
    """Tracks failure fingerprints and raises DampedAttempt when threshold exceeded."""

    def __init__(self, cfg: DampConfig) -> None:
        self._cfg = cfg
        self._buckets: Dict[str, _Bucket] = {}

    # ------------------------------------------------------------------
    def _make_fingerprint(self, exit_code: int, stderr: Optional[str]) -> str:
        parts = str(exit_code)
        if self._cfg.fingerprint_stderr and stderr:
            digest = hashlib.sha1(stderr.encode("utf-8", errors="replace")).hexdigest()[:12]
            parts = f"{exit_code}:{digest}"
        return parts

    def _evict(self, bucket: _Bucket, now: float) -> None:
        cutoff = now - self._cfg.window_seconds
        bucket.timestamps = [t for t in bucket.timestamps if t >= cutoff]

    def record_failure(self, exit_code: int, stderr: Optional[str] = None) -> None:
        """Record a failure; raise DampedAttempt if threshold is exceeded."""
        if not self._cfg.enabled:
            return
        fp = self._make_fingerprint(exit_code, stderr)
        bucket = self._buckets.setdefault(fp, _Bucket())
        now = time.monotonic()
        self._evict(bucket, now)
        bucket.timestamps.append(now)
        if len(bucket.timestamps) > self._cfg.threshold:
            raise DampedAttempt(fp, len(bucket.timestamps))

    def record_success(self) -> None:
        """Clear all buckets on a clean success."""
        self._buckets.clear()
