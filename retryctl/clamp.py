"""clamp.py — enforce min/max attempt count bounds on a retry run."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class ClampConfig:
    enabled: bool = False
    min_attempts: int = 1
    max_attempts: int = 0  # 0 means no upper bound

    def __post_init__(self) -> None:
        if self.min_attempts < 1:
            raise ValueError("clamp.min_attempts must be >= 1")
        if self.max_attempts != 0 and self.max_attempts < self.min_attempts:
            raise ValueError(
                "clamp.max_attempts must be >= min_attempts (or 0 to disable)"
            )

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "ClampConfig":
        if not isinstance(raw, dict):
            raise TypeError(f"clamp config must be a dict, got {type(raw).__name__}")
        min_a = int(raw.get("min_attempts", 1))
        max_a = int(raw.get("max_attempts", 0))
        explicit_enabled = raw.get("enabled")
        enabled = bool(explicit_enabled) if explicit_enabled is not None else (
            min_a != 1 or max_a != 0
        )
        return cls(enabled=enabled, min_attempts=min_a, max_attempts=max_a)


class ClampViolation(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message

    def __str__(self) -> str:
        return self.message


def enforce_min(cfg: ClampConfig, attempts_so_far: int) -> None:
    """Raise ClampViolation if we have not yet met the minimum attempt floor."""
    if not cfg.enabled:
        return
    if attempts_so_far < cfg.min_attempts:
        raise ClampViolation(
            f"clamp: minimum {cfg.min_attempts} attempt(s) required, "
            f"only {attempts_so_far} completed"
        )


def enforce_max(cfg: ClampConfig, next_attempt: int) -> None:
    """Raise ClampViolation if the next attempt would exceed the ceiling."""
    if not cfg.enabled:
        return
    if cfg.max_attempts != 0 and next_attempt > cfg.max_attempts:
        raise ClampViolation(
            f"clamp: attempt {next_attempt} would exceed max_attempts={cfg.max_attempts}"
        )


def describe_clamp(cfg: ClampConfig) -> str:
    if not cfg.enabled:
        return "clamp disabled"
    parts = [f"min={cfg.min_attempts}"]
    if cfg.max_attempts:
        parts.append(f"max={cfg.max_attempts}")
    else:
        parts.append("max=unlimited")
    return "clamp(" + ", ".join(parts) + ")"
