"""Jitter strategies for retry delays."""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class JitterStrategy(str, Enum):
    NONE = "none"
    FULL = "full"
    EQUAL = "equal"
    DECORRELATED = "decorrelated"


@dataclass
class JitterConfig:
    strategy: JitterStrategy = JitterStrategy.NONE
    max_ms: Optional[int] = None  # hard cap on jitter added, in milliseconds
    seed: Optional[int] = None    # for reproducible tests

    @classmethod
    def from_dict(cls, data: dict) -> "JitterConfig":
        raw = data.get("strategy", "none")
        try:
            strategy = JitterStrategy(raw)
        except ValueError:
            raise ValueError(
                f"Unknown jitter strategy {raw!r}. "
                f"Valid options: {[s.value for s in JitterStrategy]}"
            )
        max_ms = data.get("max_ms")
        if max_ms is not None:
            max_ms = int(max_ms)
            if max_ms < 0:
                raise ValueError("jitter max_ms must be >= 0")
        seed = data.get("seed")
        return cls(strategy=strategy, max_ms=max_ms, seed=seed)


def apply_jitter(base_delay: float, cfg: JitterConfig, prev_delay: float = 0.0) -> float:
    """Return a new delay with jitter applied according to cfg.

    Args:
        base_delay:  The computed delay before jitter (seconds).
        cfg:         Jitter configuration.
        prev_delay:  The previous delay used (needed for decorrelated strategy).

    Returns:
        Adjusted delay in seconds (never negative).
    """
    rng = random.Random(cfg.seed)

    if cfg.strategy == JitterStrategy.NONE:
        result = base_delay

    elif cfg.strategy == JitterStrategy.FULL:
        # Uniform sample in [0, base_delay]
        result = rng.uniform(0, base_delay)

    elif cfg.strategy == JitterStrategy.EQUAL:
        # Half fixed, half random: base/2 + uniform(0, base/2)
        half = base_delay / 2.0
        result = half + rng.uniform(0, half)

    elif cfg.strategy == JitterStrategy.DECORRELATED:
        # AWS-style: uniform(base_delay, prev_delay * 3) clamped to base_delay min
        upper = max(base_delay, prev_delay * 3)
        result = rng.uniform(base_delay, upper)

    else:
        result = base_delay

    if cfg.max_ms is not None:
        cap = cfg.max_ms / 1000.0
        # Clamp the *added* jitter, not the total, by capping total at base + cap
        result = min(result, base_delay + cap)

    return max(0.0, result)
