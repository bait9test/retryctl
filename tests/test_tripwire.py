"""Tests for retryctl.tripwire."""
from __future__ import annotations

import pytest

from retryctl.tripwire import (
    TripwireConfig,
    TripwireState,
    TripwireTripped,
)


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def test_config_defaults():
    cfg = TripwireConfig()
    assert cfg.enabled is False
    assert cfg.threshold == 3
    assert cfg.reset_on_success is True


def test_from_dict_empty_uses_defaults():
    cfg = TripwireConfig.from_dict({})
    # threshold defaults to 3 which is > 0 so enabled becomes True
    assert cfg.threshold == 3
    assert cfg.reset_on_success is True


def test_from_dict_full():
    cfg = TripwireConfig.from_dict({"enabled": True, "threshold": 5, "reset_on_success": False})
    assert cfg.enabled is True
    assert cfg.threshold == 5
    assert cfg.reset_on_success is False


def test_from_dict_invalid_type_raises():
    with pytest.raises(TypeError):
        TripwireConfig.from_dict("bad")


def test_from_dict_zero_threshold_raises():
    with pytest.raises(ValueError):
        TripwireConfig.from_dict({"threshold": 0})


def test_from_dict_negative_threshold_raises():
    with pytest.raises(ValueError):
        TripwireConfig.from_dict({"threshold": -1})


# ---------------------------------------------------------------------------
# State — disabled
# ---------------------------------------------------------------------------

def test_disabled_never_trips():
    cfg = TripwireConfig(enabled=False, threshold=1)
    state = TripwireState()
    state.record_failure(cfg)
    state.check(cfg)  # should not raise
    assert not state.tripped


# ---------------------------------------------------------------------------
# State — enabled
# ---------------------------------------------------------------------------

def test_not_tripped_below_threshold():
    cfg = TripwireConfig(enabled=True, threshold=3)
    state = TripwireState()
    state.record_failure(cfg)
    state.record_failure(cfg)
    assert not state.tripped
    state.check(cfg)  # still fine


def test_trips_at_threshold():
    cfg = TripwireConfig(enabled=True, threshold=2)
    state = TripwireState()
    state.record_failure(cfg)
    state.record_failure(cfg)
    assert state.tripped


def test_check_raises_when_tripped():
    cfg = TripwireConfig(enabled=True, threshold=1)
    state = TripwireState()
    state.record_failure(cfg, key="mykey")
    with pytest.raises(TripwireTripped) as exc_info:
        state.check(cfg, key="mykey")
    assert "mykey" in str(exc_info.value)
    assert exc_info.value.threshold == 1


def test_reset_on_success_clears_state():
    cfg = TripwireConfig(enabled=True, threshold=2, reset_on_success=True)
    state = TripwireState()
    state.record_failure(cfg)
    state.record_failure(cfg)
    assert state.tripped
    state.record_success(cfg)
    assert not state.tripped
    assert state.failures == 0


def test_no_reset_on_success_keeps_tripped():
    cfg = TripwireConfig(enabled=True, threshold=2, reset_on_success=False)
    state = TripwireState()
    state.record_failure(cfg)
    state.record_failure(cfg)
    state.record_success(cfg)
    assert state.tripped


def test_failure_count_increments():
    cfg = TripwireConfig(enabled=True, threshold=10)
    state = TripwireState()
    for i in range(4):
        state.record_failure(cfg)
    assert state.failures == 4
