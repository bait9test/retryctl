"""Tests for retryctl.cordon and retryctl.cordon_middleware."""
from __future__ import annotations

import time
import pytest

from retryctl.cordon import (
    CordonConfig,
    CordonBlocked,
    _sanitise_key,
    _state_path,
    check_cordon,
    record_cordon_failure,
    reset_cordon,
)
from retryctl.cordon_middleware import (
    parse_cordon,
    cordon_config_to_dict,
    enforce_cordon_gate,
    on_attempt_failure,
    on_run_success,
    describe_cordon,
)


# ---------------------------------------------------------------------------
# CordonConfig
# ---------------------------------------------------------------------------

def test_config_defaults():
    cfg = CordonConfig()
    assert cfg.enabled is False
    assert cfg.threshold == 5
    assert cfg.window_seconds == 60.0
    assert cfg.duration_seconds == 300.0
    assert cfg.key is None


def test_config_from_dict_full():
    cfg = CordonConfig.from_dict({
        "enabled": True,
        "threshold": 3,
        "window_seconds": 30.0,
        "duration_seconds": 120.0,
        "key": "my-job",
    })
    assert cfg.enabled is True
    assert cfg.threshold == 3
    assert cfg.window_seconds == 30.0
    assert cfg.duration_seconds == 120.0
    assert cfg.key == "my-job"


def test_config_from_dict_empty_uses_defaults():
    cfg = CordonConfig.from_dict({})
    assert cfg.threshold == 5
    assert cfg.enabled is False


def test_config_auto_enables_when_threshold_set():
    cfg = CordonConfig.from_dict({"threshold": 2})
    assert cfg.enabled is True


def test_config_from_dict_invalid_type_raises():
    with pytest.raises(TypeError):
        CordonConfig.from_dict("bad")


def test_config_zero_threshold_raises():
    with pytest.raises(ValueError):
        CordonConfig.from_dict({"threshold": 0})


def test_config_zero_window_raises():
    with pytest.raises(ValueError):
        CordonConfig.from_dict({"window_seconds": 0})


def test_config_zero_duration_raises():
    with pytest.raises(ValueError):
        CordonConfig.from_dict({"duration_seconds": 0})


# ---------------------------------------------------------------------------
# Key helpers
# ---------------------------------------------------------------------------

def test_sanitise_key_replaces_spaces():
    assert _sanitise_key("my job") == "my_job"


def test_sanitise_key_truncates_long_keys():
    long = "x" * 100
    assert len(_sanitise_key(long)) == 64


# ---------------------------------------------------------------------------
# Cordon logic (tmp dir)
# ---------------------------------------------------------------------------

def _cfg(tmp_path, threshold=2, window=60.0, duration=300.0):
    return CordonConfig(
        enabled=True,
        threshold=threshold,
        window_seconds=window,
        duration_seconds=duration,
        lock_dir=str(tmp_path),
    )


def test_disabled_cordon_never_blocks(tmp_path):
    cfg = CordonConfig(enabled=False, lock_dir=str(tmp_path))
    for _ in range(20):
        record_cordon_failure(cfg, "k")
    check_cordon(cfg, "k")  # should not raise


def test_below_threshold_does_not_cordon(tmp_path):
    cfg = _cfg(tmp_path, threshold=3)
    record_cordon_failure(cfg, "k")
    record_cordon_failure(cfg, "k")
    check_cordon(cfg, "k")  # 2 < 3, should not raise


def test_at_threshold_cordons(tmp_path):
    cfg = _cfg(tmp_path, threshold=3)
    for _ in range(3):
        record_cordon_failure(cfg, "k")
    with pytest.raises(CordonBlocked):
        check_cordon(cfg, "k")


def test_reset_clears_cordon(tmp_path):
    cfg = _cfg(tmp_path, threshold=2)
    record_cordon_failure(cfg, "k")
    record_cordon_failure(cfg, "k")
    with pytest.raises(CordonBlocked):
        check_cordon(cfg, "k")
    reset_cordon(cfg, "k")
    check_cordon(cfg, "k")  # should not raise after reset


def test_different_keys_independent(tmp_path):
    cfg = _cfg(tmp_path, threshold=2)
    record_cordon_failure(cfg, "a")
    record_cordon_failure(cfg, "a")
    check_cordon(cfg, "b")  # b is unaffected


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

def test_parse_cordon_empty_config():
    cfg = parse_cordon({})
    assert cfg.enabled is False


def test_parse_cordon_full_section():
    cfg = parse_cordon({"cordon": {"threshold": 4, "enabled": True}})
    assert cfg.threshold == 4
    assert cfg.enabled is True


def test_parse_cordon_invalid_type_raises():
    with pytest.raises(TypeError):
        parse_cordon({"cordon": "bad"})


def test_cordon_config_to_dict_roundtrip(tmp_path):
    cfg = _cfg(tmp_path, threshold=3, window=45.0, duration=180.0)
    d = cordon_config_to_dict(cfg)
    assert d["threshold"] == 3
    assert d["window_seconds"] == 45.0
    assert d["duration_seconds"] == 180.0


def test_describe_cordon_disabled():
    cfg = CordonConfig(enabled=False)
    assert "disabled" in describe_cordon(cfg)


def test_describe_cordon_enabled():
    cfg = CordonConfig(enabled=True, threshold=3, window_seconds=30.0, duration_seconds=120.0)
    desc = describe_cordon(cfg)
    assert "3" in desc
    assert "30" in desc


def test_enforce_gate_raises_when_cordoned(tmp_path):
    cfg = _cfg(tmp_path, threshold=1)
    on_attempt_failure(cfg, "k")
    with pytest.raises(CordonBlocked):
        enforce_cordon_gate(cfg, "k")


def test_on_run_success_clears_state(tmp_path):
    cfg = _cfg(tmp_path, threshold=1)
    on_attempt_failure(cfg, "k")
    on_run_success(cfg, "k")
    enforce_cordon_gate(cfg, "k")  # should not raise
