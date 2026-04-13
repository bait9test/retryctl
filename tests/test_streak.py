"""Tests for retryctl/streak.py"""
import pytest
from retryctl.streak import StreakConfig, StreakState, check_streak_warning


# ---------------------------------------------------------------------------
# StreakConfig
# ---------------------------------------------------------------------------

def test_config_defaults():
    cfg = StreakConfig()
    assert cfg.enabled is False
    assert cfg.warn_on_failure_streak == 0
    assert cfg.reset_on_success is True


def test_from_dict_full():
    cfg = StreakConfig.from_dict({"enabled": True, "warn_on_failure_streak": 3, "reset_on_success": False})
    assert cfg.enabled is True
    assert cfg.warn_on_failure_streak == 3
    assert cfg.reset_on_success is False


def test_from_dict_auto_enables_when_threshold_set():
    cfg = StreakConfig.from_dict({"warn_on_failure_streak": 5})
    assert cfg.enabled is True


def test_from_dict_empty_uses_defaults():
    cfg = StreakConfig.from_dict({})
    assert cfg.enabled is False
    assert cfg.warn_on_failure_streak == 0


def test_from_dict_invalid_type_raises():
    with pytest.raises(TypeError):
        StreakConfig.from_dict("bad")


def test_from_dict_negative_threshold_raises():
    with pytest.raises(ValueError):
        StreakConfig.from_dict({"warn_on_failure_streak": -1})


# ---------------------------------------------------------------------------
# StreakState
# ---------------------------------------------------------------------------

def test_initial_state():
    s = StreakState()
    assert s.consecutive_failures == 0
    assert s.consecutive_successes == 0


def test_record_failure_increments_failures():
    s = StreakState()
    s.record_failure()
    s.record_failure()
    assert s.consecutive_failures == 2
    assert s.consecutive_successes == 0


def test_record_success_resets_failures():
    s = StreakState()
    s.record_failure()
    s.record_failure()
    s.record_success()
    assert s.consecutive_failures == 0
    assert s.consecutive_successes == 1


def test_record_failure_resets_successes():
    s = StreakState()
    s.record_success()
    s.record_success()
    s.record_failure()
    assert s.consecutive_successes == 0
    assert s.consecutive_failures == 1


def test_roundtrip_to_from_dict():
    s = StreakState()
    s.record_failure()
    s.record_failure()
    d = s.to_dict()
    s2 = StreakState.from_dict(d)
    assert s2.consecutive_failures == 2
    assert s2.consecutive_successes == 0


# ---------------------------------------------------------------------------
# check_streak_warning
# ---------------------------------------------------------------------------

def test_warning_below_threshold_returns_none():
    cfg = StreakConfig(enabled=True, warn_on_failure_streak=3)
    state = StreakState()
    state.record_failure()
    state.record_failure()
    assert check_streak_warning(cfg, state) is None


def test_warning_at_threshold_returns_message():
    cfg = StreakConfig(enabled=True, warn_on_failure_streak=3)
    state = StreakState()
    for _ in range(3):
        state.record_failure()
    msg = check_streak_warning(cfg, state)
    assert msg is not None
    assert "3" in msg


def test_warning_disabled_cfg_returns_none():
    cfg = StreakConfig(enabled=False, warn_on_failure_streak=1)
    state = StreakState()
    state.record_failure()
    assert check_streak_warning(cfg, state) is None


def test_warning_zero_threshold_never_warns():
    cfg = StreakConfig(enabled=True, warn_on_failure_streak=0)
    state = StreakState()
    for _ in range(10):
        state.record_failure()
    assert check_streak_warning(cfg, state) is None
