"""Pulse: periodic heartbeat emission during long retry runs."""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Callable, Optional

log = logging.getLogger(__name__)


@dataclass
class PulseConfig:
    enabled: bool = False
    interval_seconds: float = 30.0
    channel: str = "log"  # log | stderr
    message: str = "retryctl heartbeat: still running (attempt {attempt})"

    @classmethod
    def from_dict(cls, raw: dict) -> "PulseConfig":
        if not isinstance(raw, dict):
            raise TypeError(f"pulse config must be a dict, got {type(raw).__name__}")
        interval = float(raw.get("interval_seconds", 30.0))
        if interval <= 0:
            raise ValueError("pulse interval_seconds must be positive")
        enabled = bool(raw.get("enabled", False))
        channel = str(raw.get("channel", "log"))
        if channel not in ("log", "stderr"):
            raise ValueError(f"pulse channel must be 'log' or 'stderr', got {channel!r}")
        message = str(raw.get("message", cls.message))
        return cls(enabled=enabled, interval_seconds=interval, channel=channel, message=message)


@dataclass
class PulseEmitter:
    config: PulseConfig
    _last_pulse: float = field(default_factory=time.monotonic, init=False)

    def reset(self) -> None:
        """Reset the pulse timer (call at the start of each attempt)."""
        self._last_pulse = time.monotonic()

    def maybe_emit(self, attempt: int, emit_fn: Optional[Callable[[str], None]] = None) -> bool:
        """Emit a heartbeat if the interval has elapsed. Returns True if emitted."""
        if not self.config.enabled:
            return False
        now = time.monotonic()
        if now - self._last_pulse < self.config.interval_seconds:
            return False
        self._last_pulse = now
        msg = self.config.message.format(attempt=attempt)
        if emit_fn is not None:
            emit_fn(msg)
        elif self.config.channel == "log":
            log.info(msg)
        else:
            import sys
            print(msg, file=sys.stderr)
        return True


def describe_pulse(cfg: PulseConfig) -> str:
    if not cfg.enabled:
        return "pulse disabled"
    return f"pulse every {cfg.interval_seconds}s via {cfg.channel}"
