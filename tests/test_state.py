"""Tests for persistent state tracking."""

import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from retryctl.state import (
    StateConfig,
    RetryState,
    load_state,
    save_state,
    clear_state,
    _state_file_path,
)


def test_state_config_defaults():
    cfg = StateConfig()
    assert cfg.enabled is False
    assert cfg.state_dir == "/tmp/retryctl/state"
    assert cfg.ttl_seconds == 86400


def test_retry_state_to_dict():
    state = RetryState(
        command_hash="abc123",
        total_attempts=5,
        first_attempt_at="2024-01-01T12:00:00",
        last_attempt_at="2024-01-01T12:05:00",
        last_exit_code=1,
        consecutive_failures=3,
    )
    data = state.to_dict()
    assert data["command_hash"] == "abc123"
    assert data["total_attempts"] == 5
    assert data["consecutive_failures"] == 3


def test_retry_state_from_dict():
    data = {
        "command_hash": "xyz789",
        "total_attempts": 2,
        "first_attempt_at": "2024-01-01T10:00:00",
        "last_attempt_at": "2024-01-01T10:01:00",
        "last_exit_code": 2,
        "consecutive_failures": 2,
    }
    state = RetryState.from_dict(data)
    assert state.command_hash == "xyz789"
    assert state.total_attempts == 2
    assert state.last_exit_code == 2


def test_state_file_path():
    cfg = StateConfig(state_dir="/custom/path")
    path = _state_file_path(cfg, "hash123")
    assert path == Path("/custom/path/hash123.json")


def test_load_state_disabled_returns_none():
    cfg = StateConfig(enabled=False)
    state = load_state(cfg, "any_hash")
    assert state is None


def test_save_and_load_state():
    with tempfile.TemporaryDirectory() as tmpdir:
        cfg = StateConfig(enabled=True, state_dir=tmpdir)
        now = datetime.now().isoformat()
        
        original = RetryState(
            command_hash="test_hash",
            total_attempts=3,
            first_attempt_at=now,
            last_attempt_at=now,
            last_exit_code=1,
            consecutive_failures=2,
        )
        
        save_state(cfg, original)
        loaded = load_state(cfg, "test_hash")
        
        assert loaded is not None
        assert loaded.command_hash == "test_hash"
        assert loaded.total_attempts == 3
        assert loaded.consecutive_failures == 2


def test_load_state_expired_returns_none():
    with tempfile.TemporaryDirectory() as tmpdir:
        cfg = StateConfig(enabled=True, state_dir=tmpdir, ttl_seconds=10)
        old_time = (datetime.now() - timedelta(seconds=20)).isoformat()
        
        state = RetryState(
            command_hash="expired",
            total_attempts=1,
            first_attempt_at=old_time,
            last_attempt_at=old_time,
            last_exit_code=1,
            consecutive_failures=1,
        )
        
        save_state(cfg, state)
        loaded = load_state(cfg, "expired")
        
        assert loaded is None


def test_load_state_missing_file_returns_none():
    with tempfile.TemporaryDirectory() as tmpdir:
        cfg = StateConfig(enabled=True, state_dir=tmpdir)
        state = load_state(cfg, "nonexistent")
        assert state is None


def test_clear_state_removes_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        cfg = StateConfig(enabled=True, state_dir=tmpdir)
        now = datetime.now().isoformat()
        
        state = RetryState(
            command_hash="to_clear",
            total_attempts=1,
            first_attempt_at=now,
            last_attempt_at=now,
            last_exit_code=0,
            consecutive_failures=0,
        )
        
        save_state(cfg, state)
        assert load_state(cfg, "to_clear") is not None
        
        clear_state(cfg, "to_clear")
        assert load_state(cfg, "to_clear") is None


def test_save_state_disabled_does_nothing():
    with tempfile.TemporaryDirectory() as tmpdir:
        cfg = StateConfig(enabled=False, state_dir=tmpdir)
        now = datetime.now().isoformat()
        
        state = RetryState(
            command_hash="disabled",
            total_attempts=1,
            first_attempt_at=now,
            last_attempt_at=now,
            last_exit_code=0,
            consecutive_failures=0,
        )
        
        save_state(cfg, state)
        
        # File should not exist
        state_file = _state_file_path(cfg, "disabled")
        assert not state_file.exists()
