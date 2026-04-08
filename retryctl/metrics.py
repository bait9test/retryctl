"""Lightweight in-process metrics collector for retry runs."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class AttemptRecord:
    attempt: int
    exit_code: int
    duration_seconds: float
    delay_before_next: Optional[float] = None  # None on last attempt


@dataclass
class RunMetrics:
    command: str
    started_at: float = field(default_factory=time.time)
    attempts: List[AttemptRecord] = field(default_factory=list)
    succeeded: bool = False
    finished_at: Optional[float] = None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def record_attempt(
        self,
        attempt: int,
        exit_code: int,
        duration_seconds: float,
        delay_before_next: Optional[float] = None,
    ) -> None:
        self.attempts.append(
            AttemptRecord(
                attempt=attempt,
                exit_code=exit_code,
                duration_seconds=duration_seconds,
                delay_before_next=delay_before_next,
            )
        )

    def finish(self, succeeded: bool) -> None:
        self.succeeded = succeeded
        self.finished_at = time.time()

    @property
    def total_attempts(self) -> int:
        return len(self.attempts)

    @property
    def total_duration_seconds(self) -> float:
        if self.finished_at is None:
            return time.time() - self.started_at
        return self.finished_at - self.started_at

    @property
    def total_delay_seconds(self) -> float:
        return sum(
            r.delay_before_next for r in self.attempts if r.delay_before_next is not None
        )

    def summary(self) -> dict:
        return {
            "command": self.command,
            "succeeded": self.succeeded,
            "total_attempts": self.total_attempts,
            "total_duration_seconds": round(self.total_duration_seconds, 4),
            "total_delay_seconds": round(self.total_delay_seconds, 4),
            "attempts": [
                {
                    "attempt": r.attempt,
                    "exit_code": r.exit_code,
                    "duration_seconds": round(r.duration_seconds, 4),
                    "delay_before_next": r.delay_before_next,
                }
                for r in self.attempts
            ],
        }
