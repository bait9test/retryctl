"""tripwire.py — one-shot abort trigger based on cumulative failure count.

Once the failure count hits the threshold the tripwire fires and all
subsequent attempts are blocked until the state is explicitly reset.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict

log = logging.getLogger(__name__)


@dataclass
class TripwireConfig:
    enabled: bool = False
    threshold: int = 3  # failures before the wire trips
    reset_on_success: bool = True

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TripwireConfig":
        if not isinstance(data, dict):
            raise TypeError(f"TripwireConfig expects a dict, got {type(data).__name__}")
        threshold = int(data.get("threshold", 3))
        if threshold < 1:
            raise ValueError("tripwire threshold must be >= 1")
        enabled = bool(data.get("enabled", threshold > 0))
        reset_on_success = bool(data.get("reset_on_success", True))
        return cls(enabled=enabled, threshold=threshold, reset_on_success=reset_on_success)


class TripwireTripped(Exception):
    def __init__(self, key: str, threshold: int) -> None:
        self.key = key
        self.threshold = threshold
        super().__init__(
            f"Tripwire '{key}' has tripped after {threshold} consecutive failures"
        )


@dataclass
class TripwireState:
    _failures: int = field(default=0, repr=False)
    _tripped: bool = field(default=False, repr=False)

    @property
    def tripped(self) -> bool:
        return self._tripped

    @property
    def failures(self) -> int:
        return self._failures

    def record_failure(self, cfg: TripwireConfig, key: str = "default") -> None:
        if not cfg.enabled:
            return
        self._failures += 1
        log.debug("tripwire '%s': failure count=%d threshold=%d", key, self._failures, cfg.threshold)
        if self._failures >= cfg.threshold:
            self._tripped = True
            log.warning("tripwire '%s' tripped at %d failures", key, self._failures)

    def check(self, cfg: TripwireConfig, key: str = "default") -> None:
        if not cfg.enabled:
            return
        if self._tripped:
            raise TripwireTripped(key, cfg.threshold)

    def record_success(self, cfg: TripwireConfig) -> None:
        if not cfg.enabled:
            return
        if cfg.reset_on_success:
            self._failures = 0
            self._tripped = False
            log.debug("tripwire reset after success")
