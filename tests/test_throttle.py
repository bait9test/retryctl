"""Tests for retryctl.throttle and retryctl.throttle_context."""

from __future__ import annotations

import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from retryctl.throttle import ThrottleConfig, ThrottleLock, _sanitise_key, _lock_path
from retryctl.throttle_context import run_throttled


# ---------------------------------------------------------------------------
# _sanitise_key
# ---------------------------------------------------------------------------

def test_sanitise_key_replaces_spaces():
    assert " " not in _sanitise_key("echo hello world")


def test_sanitise_key_truncates_long_keys():
    long_cmd = "x" * 300
    assert len(_sanitise_key(long_cmd)) == 128


def test_sanitise_key_preserves_alphanumeric():
    assert _sanitise_key("abc123") == "abc123"


# ---------------------------------------------------------------------------
# _lock_path
# ---------------------------------------------------------------------------

def test_lock_path_uses_lock_dir(tmp_path):
    cfg = ThrottleConfig(enabled=True, lock_dir=str(tmp_path))
    p = _lock_path(cfg, "mycommand")
    assert p.parent == tmp_path
    assert p.suffix == ".lock"


def test_lock_path_uses_custom_key(tmp_path):
    cfg = ThrottleConfig(enabled=True, lock_dir=str(tmp_path), lock_key="mykey")
    p = _lock_path(cfg, "ignored_command")
    assert "mykey" in p.name


# ---------------------------------------------------------------------------
# ThrottleLock acquire / release
# ---------------------------------------------------------------------------

def test_acquire_and_release(tmp_path):
    cfg = ThrottleConfig(enabled=True, lock_dir=str(tmp_path), timeout_seconds=2.0)
    lock = ThrottleLock(cfg, "echo")
    assert lock.acquire() is True
    lock.release()  # should not raise


def test_second_acquire_times_out(tmp_path):
    cfg = ThrottleConfig(enabled=True, lock_dir=str(tmp_path), timeout_seconds=0.3)
    lock1 = ThrottleLock(cfg, "echo")
    lock2 = ThrottleLock(cfg, "echo")
    assert lock1.acquire() is True
    try:
        result = lock2.acquire()
        assert result is False
    finally:
        lock1.release()


def test_context_manager_releases_on_exit(tmp_path):
    cfg = ThrottleConfig(enabled=True, lock_dir=str(tmp_path), timeout_seconds=2.0)
    with ThrottleLock(cfg, "echo") as lock:
        acquired = lock.acquire()
        assert acquired is True
    # After context exit lock should be released; a new lock should succeed.
    lock2 = ThrottleLock(cfg, "echo")
    assert lock2.acquire() is True
    lock2.release()


# ---------------------------------------------------------------------------
# run_throttled
# ---------------------------------------------------------------------------

def test_run_throttled_disabled_calls_fn_directly():
    called = []
    run_throttled(None, "cmd", lambda: called.append(True))
    assert called == [True]


def test_run_throttled_disabled_config():
    cfg = ThrottleConfig(enabled=False)
    result = run_throttled(cfg, "cmd", lambda: 42)
    assert result == 42


def test_run_throttled_raises_on_timeout(tmp_path):
    cfg = ThrottleConfig(enabled=True, lock_dir=str(tmp_path), timeout_seconds=0.2)
    outer = ThrottleLock(cfg, "cmd")
    outer.acquire()
    try:
        with pytest.raises(TimeoutError, match="throttle"):
            run_throttled(cfg, "cmd", lambda: None)
    finally:
        outer.release()


def test_run_throttled_returns_fn_value(tmp_path):
    cfg = ThrottleConfig(enabled=True, lock_dir=str(tmp_path), timeout_seconds=2.0)
    result = run_throttled(cfg, "mycommand", lambda: "ok")
    assert result == "ok"
