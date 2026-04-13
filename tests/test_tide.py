"""Tests for retryctl.tide and retryctl.tide_middleware."""
from __future__ import annotations

import pytest

from retryctl.tide import TideConfig, TideState, apply_tide
from retryctl.tide_middleware import (
    describe_tide,
    on_attempt_failure,
    on_run_success,
    parse_tide,
    scaled_delay,
    tide_config_to_dict,
)


# ---------------------------------------------------------------------------
# TideConfig
# ---------------------------------------------------------------------------

def test_config_defaults():
    cfg = TideConfig()
    assert cfg.enabled is False
    assert cfg.threshold == 3
    assert cfg.multiplier == 2.0
    assert cfg.max_multiplier == 16.0


def test_from_dict_full():
    cfg = TideConfig.from_dict(
        {"enabled": True, "threshold": 2, "multiplier": 3.0, "max_multiplier": 9.0}
    )
    assert cfg.enabled is True
    assert cfg.threshold == 2
    assert cfg.multiplier == 3.0
    assert cfg.max_multiplier == 9.0


def test_from_dict_empty_uses_defaults():
    cfg = TideConfig.from_dict({})
    assert cfg.threshold == 3
    assert cfg.multiplier == 2.0


def test_from_dict_invalid_type_raises():
    with pytest.raises(TypeError):
        TideConfig.from_dict("bad")


def test_from_dict_zero_threshold_raises():
    with pytest.raises(ValueError):
        TideConfig.from_dict({"threshold": 0})


def test_from_dict_multiplier_below_one_raises():
    with pytest.raises(ValueError):
        TideConfig.from_dict({"multiplier": 0.5})


def test_from_dict_max_multiplier_below_multiplier_raises():
    with pytest.raises(ValueError):
        TideConfig.from_dict({"multiplier": 4.0, "max_multiplier": 2.0})


# ---------------------------------------------------------------------------
# TideState
# ---------------------------------------------------------------------------

def test_initial_state():
    state = TideState()
    assert state.current_multiplier == 1.0
    assert state.consecutive_failures == 0


def test_failures_below_threshold_keep_multiplier_at_one():
    cfg = TideConfig(enabled=True, threshold=3, multiplier=2.0, max_multiplier=16.0)
    state = TideState()
    state.record_failure(cfg)
    state.record_failure(cfg)
    assert state.current_multiplier == 1.0


def test_failure_at_threshold_raises_multiplier():
    cfg = TideConfig(enabled=True, threshold=3, multiplier=2.0, max_multiplier=16.0)
    state = TideState()
    for _ in range(3):
        state.record_failure(cfg)
    assert state.current_multiplier == 2.0


def test_multiplier_grows_with_more_failures():
    cfg = TideConfig(enabled=True, threshold=2, multiplier=2.0, max_multiplier=64.0)
    state = TideState()
    for _ in range(4):  # steps: 1 -> 2x, 2 -> 4x, 3 -> 8x
        state.record_failure(cfg)
    assert state.current_multiplier == 8.0


def test_multiplier_capped_at_max():
    cfg = TideConfig(enabled=True, threshold=1, multiplier=2.0, max_multiplier=4.0)
    state = TideState()
    for _ in range(10):
        state.record_failure(cfg)
    assert state.current_multiplier == 4.0


def test_success_resets_state():
    cfg = TideConfig(enabled=True, threshold=1, multiplier=3.0, max_multiplier=27.0)
    state = TideState()
    state.record_failure(cfg)
    state.record_failure(cfg)
    state.record_success()
    assert state.current_multiplier == 1.0
    assert state.consecutive_failures == 0


# ---------------------------------------------------------------------------
# apply_tide
# ---------------------------------------------------------------------------

def test_apply_tide_disabled_returns_base():
    cfg = TideConfig(enabled=False)
    state = TideState()
    assert apply_tide(5.0, state, cfg) == 5.0


def test_apply_tide_scales_delay():
    cfg = TideConfig(enabled=True, threshold=1, multiplier=3.0, max_multiplier=27.0)
    state = TideState()
    state.record_failure(cfg)  # multiplier -> 3.0
    assert apply_tide(2.0, state, cfg) == 6.0


# ---------------------------------------------------------------------------
# Middleware helpers
# ---------------------------------------------------------------------------

def test_parse_tide_empty_config():
    cfg = parse_tide({})
    assert isinstance(cfg, TideConfig)
    assert cfg.enabled is False


def test_parse_tide_full_section():
    cfg = parse_tide({"tide": {"enabled": True, "threshold": 4}})
    assert cfg.enabled is True
    assert cfg.threshold == 4


def test_parse_tide_invalid_type_raises():
    with pytest.raises(TypeError):
        parse_tide({"tide": "oops"})


def test_tide_config_to_dict_roundtrip():
    cfg = TideConfig(enabled=True, threshold=5, multiplier=2.5, max_multiplier=20.0)
    d = tide_config_to_dict(cfg)
    assert d["threshold"] == 5
    assert d["multiplier"] == 2.5


def test_on_attempt_failure_returns_multiplier():
    cfg = TideConfig(enabled=True, threshold=1, multiplier=2.0, max_multiplier=8.0)
    state = TideState()
    m = on_attempt_failure(state, cfg)
    assert m == 2.0


def test_on_run_success_resets():
    cfg = TideConfig(enabled=True, threshold=1, multiplier=2.0, max_multiplier=8.0)
    state = TideState()
    on_attempt_failure(state, cfg)
    on_run_success(state)
    assert state.current_multiplier == 1.0


def test_scaled_delay_disabled():
    cfg = TideConfig(enabled=False)
    state = TideState()
    assert scaled_delay(3.0, state, cfg) == 3.0


def test_describe_tide_disabled():
    assert "disabled" in describe_tide(TideConfig())


def test_describe_tide_enabled():
    desc = describe_tide(TideConfig(enabled=True, threshold=3, multiplier=2.0, max_multiplier=16.0))
    assert "threshold=3" in desc
    assert "2.0x" in desc
