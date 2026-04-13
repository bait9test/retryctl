"""pivot.py — swap to an alternate command after N consecutive failures."""
from __future__ import annotations

import logging
import shlex
from dataclasses import dataclass, field
from typing import List, Optional

log = logging.getLogger(__name__)


@dataclass
class PivotConfig:
    enabled: bool = False
    threshold: int = 3          # consecutive failures before pivoting
    command: List[str] = field(default_factory=list)
    reset_on_success: bool = True

    @staticmethod
    def from_dict(raw: dict) -> "PivotConfig":
        if not isinstance(raw, dict):
            raise TypeError(f"pivot config must be a dict, got {type(raw).__name__}")

        cmd = raw.get("command", [])
        if isinstance(cmd, str):
            cmd = shlex.split(cmd)
        if not isinstance(cmd, list):
            raise TypeError("pivot.command must be a string or list")

        threshold = int(raw.get("threshold", 3))
        if threshold < 1:
            raise ValueError("pivot.threshold must be >= 1")

        enabled = bool(raw.get("enabled", bool(cmd)))

        return PivotConfig(
            enabled=enabled,
            threshold=threshold,
            command=[str(c) for c in cmd],
            reset_on_success=bool(raw.get("reset_on_success", True)),
        )


@dataclass
class PivotState:
    consecutive_failures: int = 0
    pivoted: bool = False

    def record_failure(self) -> None:
        self.consecutive_failures += 1

    def record_success(self, cfg: PivotConfig) -> None:
        if cfg.reset_on_success:
            self.consecutive_failures = 0
            self.pivoted = False

    def should_pivot(self, cfg: PivotConfig) -> bool:
        return cfg.enabled and self.consecutive_failures >= cfg.threshold


def resolve_command(
    cfg: PivotConfig,
    state: PivotState,
    original: List[str],
) -> List[str]:
    """Return the pivot command if threshold is met, otherwise the original."""
    if not cfg.enabled or not cfg.command:
        return original
    if state.should_pivot(cfg):
        if not state.pivoted:
            log.warning(
                "pivot: %d consecutive failures reached threshold %d — switching to pivot command",
                state.consecutive_failures,
                cfg.threshold,
            )
            state.pivoted = True
        return cfg.command
    return original
