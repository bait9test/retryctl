"""Timeout enforcement for command execution."""

import time
from dataclasses import dataclass
from typing import Optional


@dataclass
class TimeoutConfig:
    """Configuration for command timeout."""
    enabled: bool = False
    max_seconds: Optional[int] = None
    per_attempt: bool = True  # If False, timeout applies to total run

    @classmethod
    def from_dict(cls, data: dict) -> "TimeoutConfig":
        """Parse timeout config from dict."""
        if not data:
            return cls()
        
        max_seconds = data.get("max_seconds")
        enabled = max_seconds is not None and max_seconds > 0
        per_attempt = data.get("per_attempt", True)
        
        return cls(
            enabled=enabled,
            max_seconds=max_seconds,
            per_attempt=per_attempt
        )


class TimeoutTracker:
    """Tracks elapsed time and enforces timeout limits."""

    def __init__(self, config: TimeoutConfig):
        self.config = config
        self.run_start: Optional[float] = None
        self.attempt_start: Optional[float] = None

    def start_run(self) -> None:
        """Mark the start of the entire retry run."""
        self.run_start = time.time()

    def start_attempt(self) -> None:
        """Mark the start of a single attempt."""
        self.attempt_start = time.time()

    def is_exceeded(self) -> bool:
        """Check if timeout has been exceeded."""
        if not self.config.enabled:
            return False

        now = time.time()
        
        if self.config.per_attempt and self.attempt_start is not None:
            elapsed = now - self.attempt_start
            return elapsed > self.config.max_seconds
        
        if not self.config.per_attempt and self.run_start is not None:
            elapsed = now - self.run_start
            return elapsed > self.config.max_seconds
        
        return False

    def remaining_seconds(self) -> Optional[float]:
        """Calculate remaining seconds before timeout."""
        if not self.config.enabled:
            return None

        now = time.time()
        
        if self.config.per_attempt and self.attempt_start is not None:
            elapsed = now - self.attempt_start
            return max(0.0, self.config.max_seconds - elapsed)
        
        if not self.config.per_attempt and self.run_start is not None:
            elapsed = now - self.run_start
            return max(0.0, self.config.max_seconds - elapsed)
        
        return None
