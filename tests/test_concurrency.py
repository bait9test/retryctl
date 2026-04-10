"""Tests for retryctl.concurrency and retryctl.concurrency_middleware."""

from __future__ import annotations

import threading
import time
from unittest.mock import patch, MagicMock

import pytest

from retryctl.concurrency import (
    ConcurrencyConfig,
    ConcurrencyBlocked,
    ConcurrencyLock,
    _lock_path,
)
from retryctl.concurrency_middleware import (
    parse_concurrency,
    concurrency_config_to_dict,
    run_with_concurrency_guard,
)


# ---------------------------------------------------------------------------
# ConcurrencyConfig
# ---------------------------------------------------------------------------

def test_config_defaults():
    cfg = ConcurrencyConfig()
    assert cfg.enabled is False
    assert cfg.key is None
    assert cfg.wait is False
    assert cfg.timeout_seconds == 30.0


def test_config_from_dict_full():
    cfg = ConcurrencyConfig.from_dict({
        "enabled": True,
        "key": "my-job",
        "lock_dir": "/var/lock",
        "wait": True,
        "timeout_seconds": 10,
    })
    assert cfg.enabled is True
    assert cfg.key == "my-job"
    assert cfg.lock_dir == "/var/lock"
    assert cfg.wait is True
    assert cfg.timeout_seconds == 10.0


def test_config_from_dict_empty():
    cfg = ConcurrencyConfig.from_dict({})
    assert cfg.enabled is False


def test_lock_path_sanitises_key(tmp_path):
    cfg = ConcurrencyConfig(lock_dir=str(tmp_path))
    p = _lock_path(cfg, "hello world/cmd")
    assert " " not in p.name
    assert "/" not in p.name
    assert p.suffix == ".lock"


def test_lock_path_truncates_long_key(tmp_path):
    cfg = ConcurrencyConfig(lock_dir=str(tmp_path))
    long_key = "a" * 300
    p = _lock_path(cfg, long_key)
    # stem is at most 128 chars
    assert len(p.stem) <= 128


# ---------------------------------------------------------------------------
# ConcurrencyLock (real file locking)
# ---------------------------------------------------------------------------

def test_lock_acquire_and_release(tmp_path):
    cfg = ConcurrencyConfig(enabled=True, lock_dir=str(tmp_path))
    lock = ConcurrencyLock(cfg, "test-cmd")
    lock.acquire()
    lock.release()
    # second acquire should succeed after release
    lock.acquire()
    lock.release()


def test_lock_context_manager(tmp_path):
    cfg = ConcurrencyConfig(enabled=True, lock_dir=str(tmp_path))
    with ConcurrencyLock(cfg, "ctx-cmd"):
        pass  # should not raise


def test_lock_blocks_second_no_wait(tmp_path):
    cfg = ConcurrencyConfig(enabled=True, lock_dir=str(tmp_path), wait=False)
    first = ConcurrencyLock(cfg, "shared")
    first.acquire()
    try:
        second = ConcurrencyLock(cfg, "shared")
        with pytest.raises(ConcurrencyBlocked):
            second.acquire()
    finally:
        first.release()


# ---------------------------------------------------------------------------
# Middleware helpers
# ---------------------------------------------------------------------------

def test_parse_concurrency_empty_config():
    cfg = parse_concurrency({})
    assert cfg.enabled is False


def test_parse_concurrency_with_section():
    cfg = parse_concurrency({"concurrency": {"enabled": True, "key": "job"}})
    assert cfg.enabled is True
    assert cfg.key == "job"


def test_parse_concurrency_invalid_type_raises():
    with pytest.raises(TypeError):
        parse_concurrency({"concurrency": "bad"})


def test_concurrency_config_to_dict_roundtrip():
    cfg = ConcurrencyConfig(enabled=True, key="k", wait=True, timeout_seconds=5.0)
    d = concurrency_config_to_dict(cfg)
    cfg2 = ConcurrencyConfig.from_dict(d)
    assert cfg2.enabled == cfg.enabled
    assert cfg2.key == cfg.key
    assert cfg2.timeout_seconds == cfg.timeout_seconds


def test_run_with_guard_disabled_calls_fn():
    cfg = ConcurrencyConfig(enabled=False)
    called = []
    run_with_concurrency_guard(cfg, "cmd", lambda: called.append(1))
    assert called == [1]


def test_run_with_guard_enabled_calls_fn(tmp_path):
    cfg = ConcurrencyConfig(enabled=True, lock_dir=str(tmp_path))
    result = run_with_concurrency_guard(cfg, "cmd", lambda: 42)
    assert result == 42


def test_run_with_guard_uses_cfg_key_over_command(tmp_path):
    cfg = ConcurrencyConfig(enabled=True, key="fixed-key", lock_dir=str(tmp_path))
    # Both calls use the same key — second would block if first hadn't released
    results = []
    for _ in range(2):
        results.append(run_with_concurrency_guard(cfg, "different-cmd", lambda: True))
    assert results == [True, True]
