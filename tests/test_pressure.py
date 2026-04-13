"""Tests for retryctl/pressure.py"""
import pytest
from retryctl.pressure import PressureConfig, PressureTracker, PressureWarning


# ---------------------------------------------------------------------------
# PressureConfig
# ---------------------------------------------------------------------------

def test_config_defaults():
    cfg = PressureConfig()
    assert cfg.enabled is False
    assert cfg.threshold == 5
    assert cfg.max_pressure == 10
    assert cfg.reset_on_success is True


def test_config_from_dict_full():
    cfg = PressureConfig.from_dict(
        {"enabled": True, "threshold": 3, "max_pressure": 6, "reset_on_success": False}
    )
    assert cfg.enabled is True
    assert cfg.threshold == 3
    assert cfg.max_pressure == 6
    assert cfg.reset_on_success is False


def test_config_from_dict_empty_uses_defaults():
    cfg = PressureConfig.from_dict({})
    assert cfg.threshold == 5
    assert cfg.max_pressure == 10


def test_config_from_dict_invalid_type_raises():
    with pytest.raises(TypeError):
        PressureConfig.from_dict("not a dict")  # type: ignore


def test_config_threshold_less_than_one_raises():
    with pytest.raises(ValueError, match="threshold"):
        PressureConfig.from_dict({"threshold": 0, "max_pressure": 5})


def test_config_max_pressure_less_than_threshold_raises():
    with pytest.raises(ValueError, match="max_pressure"):
        PressureConfig.from_dict({"threshold": 5, "max_pressure": 3})


def test_config_auto_enables_when_threshold_set():
    cfg = PressureConfig.from_dict({"threshold": 2, "max_pressure": 4})
    assert cfg.enabled is True


# ---------------------------------------------------------------------------
# PressureTracker – disabled
# ---------------------------------------------------------------------------

def test_disabled_tracker_never_raises():
    cfg = PressureConfig(enabled=False, threshold=1, max_pressure=1)
    tracker = PressureTracker(cfg)
    for _ in range(20):
        tracker.record_failure()  # must not raise
    assert tracker.consecutive == 0  # not incremented when disabled


# ---------------------------------------------------------------------------
# PressureTracker – enabled
# ---------------------------------------------------------------------------

def _tracker(threshold=3, max_pressure=5, reset_on_success=True):
    cfg = PressureConfig(
        enabled=True,
        threshold=threshold,
        max_pressure=max_pressure,
        reset_on_success=reset_on_success,
    )
    return PressureTracker(cfg)


def test_failure_increments_consecutive():
    t = _tracker()
    t.record_failure()
    assert t.consecutive == 1


def test_below_threshold_does_not_raise():
    t = _tracker(threshold=3, max_pressure=5)
    t.record_failure()
    t.record_failure()  # 2 < 3 threshold, no raise
    assert t.consecutive == 2


def test_at_max_pressure_raises():
    t = _tracker(threshold=2, max_pressure=3)
    t.record_failure()
    t.record_failure()
    with pytest.raises(PressureWarning) as exc_info:
        t.record_failure()  # 3rd failure == max_pressure
    assert exc_info.value.count == 3
    assert exc_info.value.max_pressure == 3


def test_success_resets_consecutive():
    t = _tracker(reset_on_success=True)
    t.record_failure()
    t.record_failure()
    t.record_success()
    assert t.consecutive == 0


def test_success_no_reset_when_disabled():
    t = _tracker(reset_on_success=False)
    t.record_failure()
    t.record_failure()
    t.record_success()
    assert t.consecutive == 2


def test_pressure_warning_str():
    exc = PressureWarning(count=7, max_pressure=7)
    assert "7" in str(exc)
    assert "ceiling" in str(exc)
