"""Tests for retryctl/brake.py and retryctl/brake_middleware.py."""
from __future__ import annotations

import pytest

from retryctl.brake import BrakeConfig, BrakeState
from retryctl.brake_middleware import (
    brake_config_to_dict,
    describe_brake,
    make_state,
    on_attempt_failure,
    on_run_success,
    parse_brake,
)


# ---------------------------------------------------------------------------
# BrakeConfig
# ---------------------------------------------------------------------------

def test_config_defaults():
    cfg = BrakeConfig()
    assert cfg.enabled is False
    assert cfg.threshold == 3
    assert cfg.step_ms == 500
    assert cfg.max_ms == 10_000


def test_from_dict_full():
    cfg = BrakeConfig.from_dict(
        {"enabled": True, "threshold": 2, "step_ms": 200, "max_ms": 4000}
    )
    assert cfg.enabled is True
    assert cfg.threshold == 2
    assert cfg.step_ms == 200
    assert cfg.max_ms == 4000


def test_from_dict_empty_uses_defaults():
    cfg = BrakeConfig.from_dict({})
    assert cfg == BrakeConfig()


def test_from_dict_invalid_type_raises():
    with pytest.raises(TypeError):
        BrakeConfig.from_dict("bad")


def test_config_zero_threshold_raises():
    with pytest.raises(ValueError):
        BrakeConfig(threshold=0)


def test_config_negative_step_raises():
    with pytest.raises(ValueError):
        BrakeConfig(step_ms=-1)


def test_config_negative_max_raises():
    with pytest.raises(ValueError):
        BrakeConfig(max_ms=-1)


# ---------------------------------------------------------------------------
# BrakeState
# ---------------------------------------------------------------------------

def test_no_extra_delay_below_threshold():
    cfg = BrakeConfig(enabled=True, threshold=3, step_ms=500, max_ms=5000)
    state = BrakeState()
    for _ in range(3):
        extra = state.record_failure(cfg)
    assert extra == 0


def test_extra_delay_above_threshold():
    cfg = BrakeConfig(enabled=True, threshold=2, step_ms=300, max_ms=5000)
    state = BrakeState()
    state.record_failure(cfg)  # 1 – no brake
    state.record_failure(cfg)  # 2 – no brake
    extra = state.record_failure(cfg)  # 3 – brake kicks in
    assert extra == 300


def test_extra_delay_accumulates():
    cfg = BrakeConfig(enabled=True, threshold=1, step_ms=100, max_ms=5000)
    state = BrakeState()
    state.record_failure(cfg)  # 1 – no brake
    state.record_failure(cfg)  # 2 – +100
    extra = state.record_failure(cfg)  # 3 – +200
    assert extra == 200


def test_extra_delay_capped_at_max():
    cfg = BrakeConfig(enabled=True, threshold=1, step_ms=400, max_ms=500)
    state = BrakeState()
    state.record_failure(cfg)  # 1
    state.record_failure(cfg)  # 2 – +400
    extra = state.record_failure(cfg)  # 3 – would be 800, capped at 500
    assert extra == 500


def test_success_resets_state():
    cfg = BrakeConfig(enabled=True, threshold=1, step_ms=200, max_ms=2000)
    state = BrakeState()
    state.record_failure(cfg)
    state.record_failure(cfg)  # extra_ms = 200
    state.record_success()
    assert state.extra_ms == 0
    assert state.consecutive_failures == 0


# ---------------------------------------------------------------------------
# Middleware helpers
# ---------------------------------------------------------------------------

def test_parse_brake_missing_section_uses_defaults():
    cfg = parse_brake({})
    assert cfg == BrakeConfig()


def test_parse_brake_full_section():
    cfg = parse_brake({"brake": {"enabled": True, "threshold": 5}})
    assert cfg.enabled is True
    assert cfg.threshold == 5


def test_brake_config_to_dict_roundtrip():
    cfg = BrakeConfig(enabled=True, threshold=4, step_ms=250, max_ms=3000)
    d = brake_config_to_dict(cfg)
    assert BrakeConfig.from_dict(d) == cfg


def test_on_attempt_failure_disabled_returns_zero():
    cfg = BrakeConfig(enabled=False)
    state = make_state()
    for _ in range(10):
        assert on_attempt_failure(cfg, state) == 0


def test_on_run_success_disabled_is_noop():
    cfg = BrakeConfig(enabled=False)
    state = make_state()
    state._consecutive_failures = 5
    on_run_success(cfg, state)  # should not reset
    assert state.consecutive_failures == 5


def test_on_run_success_enabled_resets():
    cfg = BrakeConfig(enabled=True, threshold=1, step_ms=100, max_ms=1000)
    state = make_state()
    on_attempt_failure(cfg, state)
    on_attempt_failure(cfg, state)
    on_run_success(cfg, state)
    assert state.extra_ms == 0


def test_describe_brake_disabled():
    assert "disabled" in describe_brake(BrakeConfig())


def test_describe_brake_enabled():
    desc = describe_brake(BrakeConfig(enabled=True, threshold=3, step_ms=500, max_ms=8000))
    assert "threshold=3" in desc
    assert "step=500ms" in desc
    assert "max=8000ms" in desc
