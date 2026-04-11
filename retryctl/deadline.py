"""deadline.py — per-attempt and total-run deadline enforcement."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class DeadlineConfig:
    """Configuration for deadline enforcement."""
    per_attempt_seconds: Optional[float] = None   # max seconds for a single attempt
    total_seconds: Optional[float] = None          # max seconds for the entire run
    enabled: bool = field(init=False)

    def __post_init__(self) -> None:
        self.enabled = (
            self.per_attempt_seconds is not None
            or self.total_seconds is not None
        )

    @classmethod
    def from_dict(cls, data: dict) -> "DeadlineConfig":
        raw_attempt = data.get("per_attempt_seconds")
        raw_total = data.get("total_seconds")

        per_attempt: Optional[float] = None
        if raw_attempt is not None:
            per_attempt = float(raw_attempt)
            if per_attempt <= 0:
                raise ValueError("per_attempt_seconds must be positive")

        total: Optional[float] = None
        if raw_total is not None:
            total = float(raw_total)
            if total <= 0:
                raise ValueError("total_seconds must be positive")

        return cls(per_attempt_seconds=per_attempt, total_seconds=total)


class DeadlineExceeded(Exception):
    """Raised when a deadline has been breached."""

    def __init__(self, kind: str, limit: float) -> None:
        self.kind = kind
        self.limit = limit
        super().__init__(f"Deadline exceeded: {kind} limit of {limit:.1f}s reached")


@dataclass
class DeadlineTracker:
    """Tracks elapsed time against configured deadlines."""
    config: DeadlineConfig
    _run_start: float = field(default_factory=time.monotonic, init=False)

    def attempt_start(self) -> float:
        """Record the start of an attempt; returns the monotonic timestamp."""
        return time.monotonic()

    def check_attempt(self, attempt_start: float) -> None:
        """Raise DeadlineExceeded if the current attempt has run too long."""
        if not self.config.enabled:
            return
        limit = self.config.per_attempt_seconds
        if limit is not None and (time.monotonic() - attempt_start) >= limit:
            raise DeadlineExceeded("per_attempt", limit)

    def check_total(self) -> None:
        """Raise DeadlineExceeded if the overall run has exceeded its budget."""
        if not self.config.enabled:
            return
        limit = self.config.total_seconds
        if limit is not None and (time.monotonic() - self._run_start) >= limit:
            raise DeadlineExceeded("total", limit)

    def remaining_attempt_seconds(self, attempt_start: float) -> Optional[float]:
        """Return seconds left for the current attempt, or None if unconstrained."""
        if self.config.per_attempt_seconds is None:
            return None
        elapsed = time.monotonic() - attempt_start
        return max(0.0, self.config.per_attempt_seconds - elapsed)

    def remaining_total_seconds(self) -> Optional[float]:
        """Return seconds left for the whole run, or None if unconstrained."""
        if self.config.total_seconds is None:
            return None
        elapsed = time.monotonic() - self._run_start
        return max(0.0, self.config.total_seconds - elapsed)
