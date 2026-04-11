"""Debounce support: suppress retries that fire too rapidly in succession.

If the same command key triggers a retry within `min_interval_seconds`,
the attempt is skipped (debounced) rather than executed.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class DebounceConfig:
    enabled: bool = False
    min_interval_seconds: float = 1.0
    key: Optional[str] = None

    @staticmethod
    def from_dict(data: dict) -> "DebounceConfig":
        if not isinstance(data, dict):
            raise TypeError("debounce config must be a mapping")
        raw_interval = data.get("min_interval_seconds", 1.0)
        interval = float(raw_interval)
        if interval < 0:
            raise ValueError("min_interval_seconds must be >= 0")
        return DebounceConfig(
            enabled=bool(data.get("enabled", False)),
            min_interval_seconds=interval,
            key=data.get("key") or None,
        )


class DebounceBlocked(Exception):
    """Raised when a retry attempt is suppressed by the debounce gate."""

    def __init__(self, key: str, elapsed: float, min_interval: float) -> None:
        self.key = key
        self.elapsed = elapsed
        self.min_interval = min_interval
        super().__init__(
            f"debounce: key={key!r} fired after {elapsed:.3f}s "
            f"(min_interval={min_interval:.3f}s)"
        )


# Module-level registry: key -> last_fired timestamp
_last_fired: Dict[str, float] = {}


def _sanitise_key(key: str) -> str:
    return key.replace(" ", "_")[:128]


def record_fired(key: str) -> None:
    """Record that command *key* just fired."""
    _last_fired[_sanitise_key(key)] = time.monotonic()


def check_debounce(cfg: DebounceConfig, command: str) -> None:
    """Raise DebounceBlocked if the command fired too recently.

    Args:
        cfg: Debounce configuration.
        command: The command string (used as fallback key).
    """
    if not cfg.enabled:
        return
    key = _sanitise_key(cfg.key or command)
    last = _last_fired.get(key)
    if last is None:
        return
    elapsed = time.monotonic() - last
    if elapsed < cfg.min_interval_seconds:
        raise DebounceBlocked(key, elapsed, cfg.min_interval_seconds)


def reset_debounce(key: str) -> None:
    """Clear the debounce state for *key* (useful in tests)."""
    _last_fired.pop(_sanitise_key(key), None)
