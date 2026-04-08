"""Backoff strategies for retry delays."""

import random
from dataclasses import dataclass
from enum import Enum
from typing import Iterator


class BackoffStrategy(str, Enum):
    FIXED = "fixed"
    LINEAR = "linear"
    EXPONENTIAL = "exponential"


@dataclass
class BackoffConfig:
    strategy: BackoffStrategy = BackoffStrategy.EXPONENTIAL
    base_delay: float = 1.0
    max_delay: float = 60.0
    multiplier: float = 2.0
    jitter: bool = True


def compute_delay(attempt: int, config: BackoffConfig) -> float:
    """Compute the delay in seconds for a given attempt number (0-indexed)."""
    if config.strategy == BackoffStrategy.FIXED:
        delay = config.base_delay
    elif config.strategy == BackoffStrategy.LINEAR:
        delay = config.base_delay * (attempt + 1)
    elif config.strategy == BackoffStrategy.EXPONENTIAL:
        delay = config.base_delay * (config.multiplier ** attempt)
    else:
        raise ValueError(f"Unknown backoff strategy: {config.strategy}")

    delay = min(delay, config.max_delay)

    if config.jitter:
        delay = random.uniform(0, delay)

    return round(delay, 3)


def delay_sequence(config: BackoffConfig) -> Iterator[float]:
    """Infinite iterator yielding successive delay values."""
    attempt = 0
    while True:
        yield compute_delay(attempt, config)
        attempt += 1
