"""Persistent state tracking for retry attempts across invocations."""

import json
import os
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional


@dataclass
class StateConfig:
    """Configuration for persistent state tracking."""
    enabled: bool = False
    state_dir: str = "/tmp/retryctl/state"
    ttl_seconds: int = 86400  # 24 hours


@dataclass
class RetryState:
    """Persistent state for a specific command."""
    command_hash: str
    total_attempts: int
    first_attempt_at: str
    last_attempt_at: str
    last_exit_code: int
    consecutive_failures: int

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "RetryState":
        return cls(**data)


def _state_file_path(config: StateConfig, command_hash: str) -> Path:
    """Return the path to the state file for a given command hash."""
    state_dir = Path(config.state_dir)
    return state_dir / f"{command_hash}.json"


def load_state(config: StateConfig, command_hash: str) -> Optional[RetryState]:
    """Load persistent state for a command, or None if not found or expired."""
    if not config.enabled:
        return None

    state_file = _state_file_path(config, command_hash)
    if not state_file.exists():
        return None

    try:
        with open(state_file, 'r') as f:
            data = json.load(f)
        
        state = RetryState.from_dict(data)
        
        # Check if state is expired
        last_attempt = datetime.fromisoformat(state.last_attempt_at)
        if datetime.now() - last_attempt > timedelta(seconds=config.ttl_seconds):
            state_file.unlink(missing_ok=True)
            return None
        
        return state
    except (json.JSONDecodeError, KeyError, ValueError, OSError):
        return None


def save_state(config: StateConfig, state: RetryState) -> None:
    """Persist state for a command."""
    if not config.enabled:
        return

    state_file = _state_file_path(config, state.command_hash)
    state_file.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(state_file, 'w') as f:
            json.dump(state.to_dict(), f, indent=2)
    except OSError:
        # Silently fail if we can't write state
        pass


def clear_state(config: StateConfig, command_hash: str) -> None:
    """Remove persistent state for a command."""
    if not config.enabled:
        return

    state_file = _state_file_path(config, command_hash)
    state_file.unlink(missing_ok=True)
