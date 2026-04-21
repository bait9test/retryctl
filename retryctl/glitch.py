"""glitch.py — transient-error tolerance with a sliding acceptance window.

A GlitchTracker counts consecutive failures and only escalates once the
configured threshold is exceeded.  Failures that fall within the tolerance
window are silently absorbed so that brief, self-healing hiccups do not
trigger the full retry machinery.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class GlitchConfig:
    enabled: bool = False
    threshold: int = 2          # consecutive failures before escalating
    reset_on_success: bool = True

    def __post_init__(self) -> None:
        if self.threshold < 1:
            raise ValueError("glitch threshold must be >= 1")

    @classmethod
    def from_dict(cls, raw: dict) -> "GlitchConfig":
        if not isinstance(raw, dict):
            raise TypeError(f"glitch config must be a dict, got {type(raw).__name__}")
        threshold = int(raw.get("threshold", 2))
        reset_on_success = bool(raw.get("reset_on_success", True))
        enabled = bool(raw.get("enabled", threshold > 0))
        return cls(enabled=enabled, threshold=threshold, reset_on_success=reset_on_success)


class GlitchAbsorbed(Exception):
    """Raised when a failure is absorbed by the glitch tolerance window."""

    def __init__(self, consecutive: int, threshold: int) -> None:
        self.consecutive = consecutive
        self.threshold = threshold
        super().__init__(
            f"glitch absorbed (consecutive={consecutive}, threshold={threshold})"
        )


@dataclass
class GlitchTracker:
    config: GlitchConfig
    _consecutive: int = field(default=0, init=False)

    def on_attempt_failure(self) -> None:
        """Record a failure; raise GlitchAbsorbed if still within tolerance."""
        if not self.config.enabled:
            return
        self._consecutive += 1
        if self._consecutive <= self.config.threshold:
            raise GlitchAbsorbed(self._consecutive, self.config.threshold)

    def on_run_success(self) -> None:
        """Reset the consecutive counter on a successful run."""
        if self.config.reset_on_success:
            self._consecutive = 0

    @property
    def consecutive(self) -> int:
        return self._consecutive
