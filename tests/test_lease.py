"""Tests for ret retryctl.lease_middleware."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from retryctl.lease import (
    LeaseConfig,
    LeaseHeld,
    _sanitise_key,
    _lease_path,
    acquire_lease,
    release_lease,
)
from retryctl.lease_middleware import (
    parse_lease,
    lease_config_to_dict,
    run_with_lease,
    describe_lease,
)


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def test_config_defaults():
    cfg = LeaseConfig()
    assert cfg.enabled is False
    assert cfg.ttl_seconds == 60
    assert cfg.key == ""


def test_config_from_dict_full():
    cfg = LeaseConfig.from_dict({"key": "myjob", "ttl_seconds": 30, "enabled": True})
    assert cfg.key == "myjob"
    assert cfg.ttl_seconds == 30
    assert cfg.enabled is True


def test_config_auto_enables_when_key_set():
    cfg = LeaseConfig.from_dict({"key": "deploy"})
    assert cfg.enabled is True


def test_config_invalid_type_raises():
    with pytest.raises(TypeError):
        LeaseConfig.from_dict("bad")


def test_config_zero_ttl_raises():
    with pytest.raises(ValueError):
        LeaseConfig.from_dict({"key": "x", "ttl_seconds": 0})


# ---------------------------------------------------------------------------
# Key sanitisation
# ---------------------------------------------------------------------------

def test_sanitise_key_replaces_spaces():
    assert _sanitise_key("my job") == "my_job"


def test_sanitise_key_truncates_long_keys():
    assert len(_sanitise_key("a" * 100)) == 64


def test_sanitise_key_preserves_alphanumeric():
    assert _sanitise_key("job-1_ok") == "job-1_ok"


# ---------------------------------------------------------------------------
# Acquire / release
# ---------------------------------------------------------------------------

def test_acquire_creates_lease_file(tmp_path):
    cfg = LeaseConfig(enabled=True, key="test", lease_dir=str(tmp_path))
    path = acquire_lease(cfg)
    assert path.exists()
    data = json.loads(path.read_text())
    assert data["expires_at"] > time.time()


def test_acquire_raises_when_lease_held(tmp_path):
    cfg = LeaseConfig(enabled=True, key="test", ttl_seconds=60, lease_dir=str(tmp_path))
    acquire_lease(cfg)
    with pytest.raises(LeaseHeld) as exc_info:
        acquire_lease(cfg)
    assert "test" in str(exc_info.value)


def test_acquire_reclaims_expired_lease(tmp_path):
    cfg = LeaseConfig(enabled=True, key="test", ttl_seconds=60, lease_dir=str(tmp_path))
    path = _lease_path(cfg)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"pid": 99, "expires_at": time.time() - 1}))
    acquired = acquire_lease(cfg)
    assert acquired.exists()


def test_release_removes_file(tmp_path):
    cfg = LeaseConfig(enabled=True, key="rel", lease_dir=str(tmp_path))
    path = acquire_lease(cfg)
    release_lease(path)
    assert not path.exists()


def test_release_missing_file_does_not_raise(tmp_path):
    release_lease(tmp_path / "ghost.lease")  # should not raise


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

def test_run_with_lease_disabled_does_not_create_file(tmp_path):
    cfg = LeaseConfig(enabled=False, key="x", lease_dir=str(tmp_path))
    with run_with_lease(cfg):
        pass
    assert list(tmp_path.iterdir()) == []


def test_run_with_lease_creates_and_cleans_up(tmp_path):
    cfg = LeaseConfig(enabled=True, key="ctx", lease_dir=str(tmp_path))
    path = _lease_path(cfg)
    with run_with_lease(cfg):
        assert path.exists()
    assert not path.exists()


def test_run_with_lease_cleans_up_on_exception(tmp_path):
    cfg = LeaseConfig(enabled=True, key="err", lease_dir=str(tmp_path))
    path = _lease_path(cfg)
    with pytest.raises(RuntimeError):
        with run_with_lease(cfg):
            assert path.exists()
            raise RuntimeError("boom")
    assert not path.exists()


def test_parse_lease_empty_config():
    cfg = parse_lease({})
    assert cfg.enabled is False


def test_parse_lease_full_section():
    cfg = parse_lease({"lease": {"key": "deploy", "ttl_seconds": 120}})
    assert cfg.key == "deploy"
    assert cfg.ttl_seconds == 120


def test_parse_lease_invalid_type_raises():
    with pytest.raises(TypeError):
        parse_lease({"lease": "bad"})


def test_lease_config_to_dict_roundtrip():
    cfg = LeaseConfig(enabled=True, key="job", ttl_seconds=45, lease_dir="/tmp")
    d = lease_config_to_dict(cfg)
    assert d["key"] == "job"
    assert d["ttl_seconds"] == 45


def test_describe_lease_disabled():
    assert "disabled" in describe_lease(LeaseConfig())


def test_describe_lease_enabled():
    cfg = LeaseConfig(enabled=True, key="myjob", ttl_seconds=30)
    desc = describe_lease(cfg)
    assert "myjob" in desc
    assert "30" in desc
