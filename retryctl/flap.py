"""Flap detection: suppress retries when a command oscillates between
pass and fail too rapidly (i.e., is "flapping")."""
from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Dict


@dataclass
class FlapConfig:
    enabled: bool = False
    # number of transitions (fail->pass or pass->fail) within window_seconds
    # that triggers flap detection
    threshold: int = 4
    window_seconds: float = 60.0

    @staticmethod
    def from_dict(data: dict) -> "FlapConfig":
        if not isinstance(data, dict):
            raise TypeError(f"FlapConfig expects a dict, got {type(data).__name__}")
        threshold = int(data.get("threshold", 4))
        window = float(data.get("window_seconds", 60.0))
        if threshold < 1:
            raise ValueError("flap threshold must be >= 1")
        if window <= 0:
            raise ValueError("flap window_seconds must be > 0")
        enabled = bool(data.get("enabled", threshold > 0))
        return FlapConfig(enabled=enabled, threshold=threshold, window_seconds=window)


class FlapDetected(Exception):
    def __init__(self, key: str, transitions: int, window: float) -> None:
        self.key = key
        self.transitions = transitions
        self.window = window
        super().__init__(
            f"flap detected for '{key}': {transitions} transitions in {window}s"
        )


_registry: Dict[str, "FlapTracker"] = {}


class FlapTracker:
    def __init__(self, cfg: FlapConfig, key: str) -> None:
        self._cfg = cfg
        self._key = key
        self._transitions: Deque[float] = deque()
        self._last_outcome: bool | None = None

    def _evict(self) -> None:
        cutoff = time.monotonic() - self._cfg.window_seconds
        while self._transitions and self._transitions[0] < cutoff:
            self._transitions.popleft()

    def record(self, success: bool) -> None:
        if not self._cfg.enabled:
            return
        if self._last_outcome is not None and self._last_outcome != success:
            self._transitions.append(time.monotonic())
        self._last_outcome = success
        self._evict()
        if len(self._transitions) >= self._cfg.threshold:
            raise FlapDetected(self._key, len(self._transitions), self._cfg.window_seconds)

    @property
    def transition_count(self) -> int:
        self._evict()
        return len(self._transitions)


def get_tracker(cfg: FlapConfig, key: str) -> FlapTracker:
    if key not in _registry:
        _registry[key] = FlapTracker(cfg, key)
    return _registry[key]


def clear_registry() -> None:
    _registry.clear()
