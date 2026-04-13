"""Integration-style tests for the lease guard running through the context manager."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from retryctl.lease import (
    LeaseConfig,
    LeaseHeld,
    _lease_path,
    acquire_lease,
)
from retryctl.lease_middleware import run_with_lease


def _cfg(tmp_path: Path, key: str = "integ", ttl: int = 60) -> LeaseConfig:
    return LeaseConfig(enabled=True, key=key, ttl_seconds=ttl, lease_dir=str(tmp_path))


def test_second_context_blocked_while_first_active(tmp_path):
    cfg = _cfg(tmp_path)
    with run_with_lease(cfg):
        with pytest.raises(LeaseHeld):
            with run_with_lease(cfg):
                pass  # should not reach here


def test_second_context_succeeds_after_first_releases(tmp_path):
    cfg = _cfg(tmp_path)
    with run_with_lease(cfg):
        pass
    # lease released — second run should succeed
    with run_with_lease(cfg):
        pass


def test_different_keys_do_not_conflict(tmp_path):
    cfg_a = _cfg(tmp_path, key="job-a")
    cfg_b = _cfg(tmp_path, key="job-b")
    with run_with_lease(cfg_a):
        with run_with_lease(cfg_b):  # different key — should not raise
            pass


def test_expired_lease_does_not_block(tmp_path):
    cfg = _cfg(tmp_path, ttl=60)
    path = _lease_path(cfg)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"pid": 1, "expires_at": time.time() - 5}))
    # expired lease should be reclaimed transparently
    with run_with_lease(cfg):
        assert path.exists()


def test_lease_held_error_contains_key(tmp_path):
    cfg = _cfg(tmp_path, key="my-service")
    acquire_lease(cfg)
    with pytest.raises(LeaseHeld) as exc_info:
        acquire_lease(cfg)
    assert "my-service" in str(exc_info.value)


def test_disabled_lease_never_blocks(tmp_path):
    cfg = LeaseConfig(enabled=False, key="noop", lease_dir=str(tmp_path))
    with run_with_lease(cfg):
        with run_with_lease(cfg):  # both disabled — no conflict
            pass
