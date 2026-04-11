"""Circuit breaker support for retryctl.

Tracks consecutive failures per command key and opens the circuit
(blocks execution) once the failure threshold is reached.  The circuit
resets automatically after a configurable cool-down window.
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class CircuitConfig:
    enabled: bool = False
    failure_threshold: int = 5
    reset_seconds: int = 60
    state_dir: str = "/tmp/retryctl/circuit"

    @staticmethod
    def from_dict(data: dict) -> "CircuitConfig":
        if not isinstance(data, dict):
            raise TypeError("circuit config must be a mapping")
        cfg = CircuitConfig()
        cfg.enabled = bool(data.get("enabled", False))
        cfg.failure_threshold = int(data.get("failure_threshold", 5))
        cfg.reset_seconds = int(data.get("reset_seconds", 60))
        cfg.state_dir = str(data.get("state_dir", "/tmp/retryctl/circuit"))
        if cfg.failure_threshold < 1:
            raise ValueError("failure_threshold must be >= 1")
        if cfg.reset_seconds < 0:
            raise ValueError("reset_seconds must be >= 0")
        return cfg


class CircuitOpen(Exception):
    """Raised when the circuit is open and execution should be blocked."""

    def __init__(self, key: str, opens_until: float) -> None:
        self.key = key
        self.opens_until = opens_until
        remaining = max(0.0, opens_until - time.time())
        super().__init__(
            f"circuit open for '{key}'; resets in {remaining:.0f}s"
        )


@dataclass
class _CircuitState:
    failures: int = 0
    opened_at: Optional[float] = None


def _sanitise_key(key: str) -> str:
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in key)[:64]


def _state_path(cfg: CircuitConfig, key: str) -> Path:
    return Path(cfg.state_dir) / f"{_sanitise_key(key)}.json"


def _load_state(cfg: CircuitConfig, key: str) -> _CircuitState:
    path = _state_path(cfg, key)
    try:
        data = json.loads(path.read_text())
        return _CircuitState(
            failures=int(data.get("failures", 0)),
            opened_at=data.get("opened_at"),
        )
    except (FileNotFoundError, json.JSONDecodeError, ValueError):
        return _CircuitState()


def _save_state(cfg: CircuitConfig, key: str, state: _CircuitState) -> None:
    path = _state_path(cfg, key)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"failures": state.failures, "opened_at": state.opened_at}))


def check_circuit(cfg: CircuitConfig, key: str) -> None:
    """Raise CircuitOpen if the circuit is open, otherwise do nothing."""
    if not cfg.enabled:
        return
    state = _load_state(cfg, key)
    if state.opened_at is None:
        return
    opens_until = state.opened_at + cfg.reset_seconds
    if time.time() < opens_until:
        raise CircuitOpen(key, opens_until)
    # reset after window
    _save_state(cfg, key, _CircuitState())


def record_failure(cfg: CircuitConfig, key: str) -> None:
    """Record a failure; open the circuit if threshold is reached."""
    if not cfg.enabled:
        return
    state = _load_state(cfg, key)
    if state.opened_at is not None:
        opens_until = state.opened_at + cfg.reset_seconds
        if time.time() >= opens_until:
            state = _CircuitState()
        else:
            return  # already open
    state.failures += 1
    if state.failures >= cfg.failure_threshold:
        state.opened_at = time.time()
    _save_state(cfg, key, state)


def record_success(cfg: CircuitConfig, key: str) -> None:
    """Reset the circuit state after a successful run."""
    if not cfg.enabled:
        return
    _save_state(cfg, key, _CircuitState())
