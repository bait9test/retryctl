"""Splay — randomised startup delay to spread retry storms across a fleet."""
from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class SplayConfig:
    enabled: bool = False
    max_seconds: float = 0.0
    seed: int | None = None  # optional fixed seed for deterministic tests

    def __post_init__(self) -> None:
        if self.max_seconds < 0:
            raise ValueError("splay max_seconds must be >= 0")


def from_dict(raw: dict[str, Any]) -> SplayConfig:
    if not isinstance(raw, dict):
        raise TypeError(f"splay config must be a dict, got {type(raw).__name__}")
    max_s = float(raw.get("max_seconds", 0.0))
    enabled = bool(raw.get("enabled", max_s > 0))
    seed = raw.get("seed")  # None means use system randomness
    return SplayConfig(enabled=enabled, max_seconds=max_s, seed=seed)


class SplayBlocked(Exception):
    """Raised (internally) if splay sleep is interrupted — not normally surfaced."""


def compute_splay(cfg: SplayConfig) -> float:
    """Return a random delay in seconds within [0, max_seconds]."""
    if not cfg.enabled or cfg.max_seconds <= 0:
        return 0.0
    rng = random.Random(cfg.seed) if cfg.seed is not None else random
    return rng.uniform(0.0, cfg.max_seconds)


def apply_splay(cfg: SplayConfig) -> float:
    """Sleep for a random splay duration; return the actual seconds slept."""
    delay = compute_splay(cfg)
    if delay > 0:
        time.sleep(delay)
    return delay
