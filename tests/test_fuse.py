"""Tests for retryctl.fuse."""
from __future__ import annotations

import pytest

from retryctl.fuse import FuseConfig, FuseTracker, FuseTripped


# ---------------------------------------------------------------------------
# FuseConfig
# ---------------------------------------------------------------------------

def test_config_defaults():
    cfg = FuseConfig()
    assert cfg.enabled is False
    assert cfg.threshold == 0.8
    assert cfg.min_attempts == 3
    assert cfg.window_seconds == 0.0


def test_config_from_dict_full():
    cfg = FuseConfig.from_dict(
        {"enabled": True, "threshold": 0.5, "min_attempts": 5, "window_seconds": 60.0}
    )
    assert cfg.enabled is True
    assert cfg.threshold == 0.5
    assert cfg.min_attempts == 5
    assert cfg.window_seconds == 60.0


def test_config_from_dict_empty_uses_defaults():
    cfg = FuseConfig.from_dict({})
    assert cfg.enabled is False
    assert cfg.threshold == 0.8


def test_config_auto_enables_when_threshold_supplied():
    cfg = FuseConfig.from_dict({"threshold": 0.6})
    assert cfg.enabled is True


def test_config_invalid_type_raises():
    with pytest.raises(TypeError):
        FuseConfig.from_dict("bad")


def test_config_zero_threshold_raises():
    with pytest.raises(ValueError):
        FuseConfig(threshold=0.0)


def test_config_threshold_above_one_raises():
    with pytest.raises(ValueError):
        FuseConfig(threshold=1.1)


def test_config_negative_min_attempts_raises():
    with pytest.raises(ValueError):
        FuseConfig(min_attempts=0)


def test_config_negative_window_raises():
    with pytest.raises(ValueError):
        FuseConfig(window_seconds=-1.0)


# ---------------------------------------------------------------------------
# FuseTracker – disabled
# ---------------------------------------------------------------------------

def test_disabled_tracker_never_trips():
    cfg = FuseConfig(enabled=False)
    tracker = FuseTracker(config=cfg)
    for _ in range(20):
        tracker.record_attempt(failed=True)
    tracker.check()  # should not raise


# ---------------------------------------------------------------------------
# FuseTracker – below min_attempts
# ---------------------------------------------------------------------------

def test_below_min_attempts_does_not_trip():
    cfg = FuseConfig(enabled=True, min_attempts=5, threshold=0.5)
    tracker = FuseTracker(config=cfg)
    for _ in range(4):
        tracker.record_attempt(failed=True)
    tracker.check()  # only 4 attempts, need 5


# ---------------------------------------------------------------------------
# FuseTracker – trips at threshold
# ---------------------------------------------------------------------------

def test_trips_when_all_failures():
    cfg = FuseConfig(enabled=True, min_attempts=3, threshold=0.8)
    tracker = FuseTracker(config=cfg)
    for _ in range(5):
        tracker.record_attempt(failed=True)
    with pytest.raises(FuseTripped) as exc_info:
        tracker.check()
    assert exc_info.value.rate == 1.0


def test_does_not_trip_below_threshold():
    cfg = FuseConfig(enabled=True, min_attempts=3, threshold=0.8)
    tracker = FuseTracker(config=cfg)
    # 3 failures out of 10 = 30 % < 80 %
    for _ in range(3):
        tracker.record_attempt(failed=True)
    for _ in range(7):
        tracker.record_attempt(failed=False)
    tracker.check()


def test_trips_exactly_at_threshold():
    cfg = FuseConfig(enabled=True, min_attempts=4, threshold=0.75)
    tracker = FuseTracker(config=cfg)
    # 3 failures, 1 success = 75 %
    for _ in range(3):
        tracker.record_attempt(failed=True)
    tracker.record_attempt(failed=False)
    with pytest.raises(FuseTripped):
        tracker.check()


# ---------------------------------------------------------------------------
# FuseTripped message
# ---------------------------------------------------------------------------

def test_fuse_tripped_str():
    exc = FuseTripped(rate=0.9, threshold=0.8, attempts=10)
    msg = str(exc)
    assert "90%" in msg
    assert "80%" in msg
    assert "10" in msg
