"""slop.py — tolerance window for marginal failures.

A 'slop' tracker allows a configurable number of consecutive near-miss
failures (exit codes in a tolerance set) to pass through without counting
against the main retry budget.  Once the slop window is exhausted the
attempt is treated as a normal failure.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Collection, List, Optional


@dataclass
class SlopConfig:
    enabled: bool = False
    # exit codes considered "marginal" (not hard failures)
    tolerance_codes: List[int] = field(default_factory=list)
    # how many marginal failures are forgiven before counting as real failures
    window: int = 3

    @staticmethod
    def from_dict(data: dict) -> "SlopConfig":
        if not isinstance(data, dict):
            raise TypeError(f"SlopConfig expects a dict, got {type(data).__name__}")
        tolerance_codes = [int(c) for c in data.get("tolerance_codes", [])]
        window = int(data.get("window", 3))
        if window < 1:
            raise ValueError("slop window must be >= 1")
        enabled = bool(data.get("enabled", bool(tolerance_codes)))
        return SlopConfig(enabled=enabled, tolerance_codes=tolerance_codes, window=window)


class SlopAbsorbed(Exception):
    """Raised when a marginal failure is absorbed by the slop window."""

    def __init__(self, exit_code: int, remaining: int) -> None:
        self.exit_code = exit_code
        self.remaining = remaining
        super().__init__(
            f"exit code {exit_code} absorbed by slop (remaining={remaining})"
        )


class SlopTracker:
    """Tracks marginal failures within the tolerance window."""

    def __init__(self, cfg: SlopConfig) -> None:
        self._cfg = cfg
        self._marginal_count: int = 0

    # ------------------------------------------------------------------
    def is_marginal(self, exit_code: int) -> bool:
        return exit_code in self._cfg.tolerance_codes

    def record_marginal(self) -> int:
        """Increment marginal counter; return remaining tolerance."""
        self._marginal_count += 1
        return max(0, self._cfg.window - self._marginal_count)

    def exhausted(self) -> bool:
        return self._marginal_count >= self._cfg.window

    def reset(self) -> None:
        self._marginal_count = 0

    # ------------------------------------------------------------------
    def check(self, exit_code: int) -> None:
        """If exit_code is marginal and window not exhausted, raise SlopAbsorbed."""
        if not self._cfg.enabled:
            return
        if not self.is_marginal(exit_code):
            return
        if self.exhausted():
            return  # treat as normal failure
        remaining = self.record_marginal()
        raise SlopAbsorbed(exit_code=exit_code, remaining=remaining)
