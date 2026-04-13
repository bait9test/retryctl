"""Tests for retryctl.latch"""
from __future__ import annotations

import json
import pytest
from pathlib import Path

from retryctl.latch import (
    LatchConfig,
    LatchTripped,
    _sanitise_key,
    _latch_path,
    check_latch,
    on_attempt_failure,
    reset_latch,
)


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def test_config_defaults():
    cfg = LatchConfig()
    assert cfg.enabled is False
    assert cfg.threshold == 3
    assert cfg.key == "default"


def test_config_from_dict_full():
    cfg = LatchConfig.from_dict({"threshold": 5, "key": "my-job", "enabled": True})
    assert cfg.enabled is True
    assert cfg.threshold == 5
    assert cfg.key == "my-job"


def test_config_auto_enables_when_threshold_set():
    cfg = LatchConfig.from_dict({"threshold": 2})
    assert cfg.enabled is True


def test_config_from_dict_invalid_type_raises():
    with pytest.raises(TypeError):
        LatchConfig.from_dict("bad")


def test_config_zero_threshold_raises():
    with pytest.raises(ValueError):
        LatchConfig.from_dict({"threshold": 0})


# ---------------------------------------------------------------------------
# Key sanitisation
# ---------------------------------------------------------------------------

def test_sanitise_key_replaces_spaces():
    assert " " not in _sanitise_key("hello world")


def test_sanitise_key_truncates_long_keys():
    assert len(_sanitise_key("x" * 200)) == 64


def test_sanitise_key_preserves_alphanumeric():
    assert _sanitise_key("abc-123") == "abc-123"


# ---------------------------------------------------------------------------
# check_latch
# ---------------------------------------------------------------------------

def test_check_latch_disabled_never_raises(tmp_path):
    cfg = LatchConfig(enabled=False, lock_dir=tmp_path)
    check_latch(cfg)  # should not raise


def test_check_latch_below_threshold_does_not_raise(tmp_path):
    cfg = LatchConfig(enabled=True, threshold=3, key="t", lock_dir=tmp_path)
    path = _latch_path(cfg)
    path.write_text(json.dumps({"failures": 2}))
    check_latch(cfg)  # 2 < 3, should not raise


def test_check_latch_at_threshold_raises(tmp_path):
    cfg = LatchConfig(enabled=True, threshold=3, key="t", lock_dir=tmp_path)
    path = _latch_path(cfg)
    path.write_text(json.dumps({"failures": 3}))
    with pytest.raises(LatchTripped) as exc_info:
        check_latch(cfg)
    assert exc_info.value.failures == 3


def test_check_latch_missing_file_does_not_raise(tmp_path):
    cfg = LatchConfig(enabled=True, threshold=2, key="missing", lock_dir=tmp_path)
    check_latch(cfg)  # no file => 0 failures


# ---------------------------------------------------------------------------
# on_attempt_failure
# ---------------------------------------------------------------------------

def test_on_attempt_failure_increments(tmp_path):
    cfg = LatchConfig(enabled=True, threshold=5, key="inc", lock_dir=tmp_path)
    on_attempt_failure(cfg)
    on_attempt_failure(cfg)
    path = _latch_path(cfg)
    data = json.loads(path.read_text())
    assert data["failures"] == 2


def test_on_attempt_failure_disabled_writes_nothing(tmp_path):
    cfg = LatchConfig(enabled=False, lock_dir=tmp_path)
    on_attempt_failure(cfg)
    assert not any(tmp_path.iterdir())


# ---------------------------------------------------------------------------
# reset_latch
# ---------------------------------------------------------------------------

def test_reset_latch_removes_file(tmp_path):
    cfg = LatchConfig(enabled=True, threshold=2, key="r", lock_dir=tmp_path)
    path = _latch_path(cfg)
    path.write_text(json.dumps({"failures": 2}))
    reset_latch(cfg)
    assert not path.exists()


def test_reset_latch_missing_file_does_not_raise(tmp_path):
    cfg = LatchConfig(enabled=True, threshold=2, key="nope", lock_dir=tmp_path)
    reset_latch(cfg)  # should not raise


def test_reset_latch_disabled_does_nothing(tmp_path):
    cfg = LatchConfig(enabled=False, lock_dir=tmp_path)
    reset_latch(cfg)  # should not raise


# ---------------------------------------------------------------------------
# LatchTripped message
# ---------------------------------------------------------------------------

def test_latch_tripped_str():
    exc = LatchTripped("myjob", 4)
    assert "myjob" in str(exc)
    assert "4" in str(exc)
