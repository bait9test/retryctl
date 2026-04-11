"""Tests for retryctl.debounce."""
from __future__ import annotations

import time

import pytest

from retryctl.debounce import (
    DebounceBlocked,
    DebounceConfig,
    _last_fired,
    check_debounce,
    record_fired,
    reset_debounce,
)


# ---------------------------------------------------------------------------
# DebounceConfig
# ---------------------------------------------------------------------------

def test_config_defaults():
    cfg = DebounceConfig()
    assert cfg.enabled is False
    assert cfg.min_interval_seconds == 1.0
    assert cfg.key is None


def test_config_from_dict_full():
    cfg = DebounceConfig.from_dict({"enabled": True, "min_interval_seconds": 0.5, "key": "myjob"})
    assert cfg.enabled is True
    assert cfg.min_interval_seconds == 0.5
    assert cfg.key == "myjob"


def test_config_from_dict_empty():
    cfg = DebounceConfig.from_dict({})
    assert cfg.enabled is False


def test_config_from_dict_invalid_type_raises():
    with pytest.raises(TypeError):
        DebounceConfig.from_dict("bad")


def test_config_from_dict_negative_interval_raises():
    with pytest.raises(ValueError):
        DebounceConfig.from_dict({"min_interval_seconds": -1})


def test_config_from_dict_empty_key_becomes_none():
    cfg = DebounceConfig.from_dict({"key": ""})
    assert cfg.key is None


# ---------------------------------------------------------------------------
# check_debounce / record_fired
# ---------------------------------------------------------------------------

def test_disabled_config_never_raises():
    cfg = DebounceConfig(enabled=False, min_interval_seconds=100.0, key="k")
    record_fired("k")
    # Should not raise even though we just fired
    check_debounce(cfg, "k")
    reset_debounce("k")


def test_no_prior_fire_does_not_raise():
    reset_debounce("fresh_key")
    cfg = DebounceConfig(enabled=True, min_interval_seconds=5.0, key="fresh_key")
    check_debounce(cfg, "fresh_key")  # no prior record — should pass


def test_rapid_fire_raises_debounce_blocked():
    key = "rapid"
    reset_debounce(key)
    cfg = DebounceConfig(enabled=True, min_interval_seconds=60.0, key=key)
    record_fired(key)
    with pytest.raises(DebounceBlocked) as exc_info:
        check_debounce(cfg, key)
    err = exc_info.value
    assert err.key == key
    assert err.elapsed < 60.0
    assert err.min_interval == 60.0
    reset_debounce(key)


def test_after_interval_passes_no_raise(monkeypatch):
    key = "slow"
    reset_debounce(key)
    cfg = DebounceConfig(enabled=True, min_interval_seconds=0.01, key=key)
    record_fired(key)
    time.sleep(0.02)
    check_debounce(cfg, key)  # enough time has passed
    reset_debounce(key)


def test_command_used_as_fallback_key():
    cmd = "echo hello"
    reset_debounce(cmd)
    cfg = DebounceConfig(enabled=True, min_interval_seconds=60.0)  # key=None
    record_fired(cmd)
    with pytest.raises(DebounceBlocked):
        check_debounce(cfg, cmd)
    reset_debounce(cmd)


def test_debounce_blocked_str_contains_key():
    err = DebounceBlocked("mykey", 0.001, 1.0)
    assert "mykey" in str(err)
    assert "0.001" in str(err)
