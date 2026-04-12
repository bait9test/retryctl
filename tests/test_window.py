"""Tests for retryctl/window.py"""
import pytest
from retryctl.window import WindowConfig, WindowBreached, WindowTracker


# ---------------------------------------------------------------------------
# WindowConfig
# ---------------------------------------------------------------------------

def test_config_defaults():
    cfg = WindowConfig()
    assert cfg.enabled is False
    assert cfg.window_seconds == 60.0
    assert cfg.min_attempts == 3
    assert cfg.max_failure_rate == 0.5


def test_config_from_dict_full():
    cfg = WindowConfig.from_dict(
        {"enabled": True, "window_seconds": 30.0, "min_attempts": 5, "max_failure_rate": 0.8}
    )
    assert cfg.enabled is True
    assert cfg.window_seconds == 30.0
    assert cfg.min_attempts == 5
    assert cfg.max_failure_rate == 0.8


def test_config_from_dict_empty_uses_defaults():
    cfg = WindowConfig.from_dict({})
    assert cfg.window_seconds == 60.0
    assert cfg.min_attempts == 3


def test_config_from_dict_invalid_type_raises():
    with pytest.raises(TypeError):
        WindowConfig.from_dict("bad")


def test_config_zero_window_raises():
    with pytest.raises(ValueError, match="window_seconds"):
        WindowConfig.from_dict({"window_seconds": 0})


def test_config_zero_min_attempts_raises():
    with pytest.raises(ValueError, match="min_attempts"):
        WindowConfig.from_dict({"min_attempts": 0})


def test_config_invalid_failure_rate_raises():
    with pytest.raises(ValueError, match="max_failure_rate"):
        WindowConfig.from_dict({"max_failure_rate": 0.0})


def test_config_failure_rate_above_one_raises():
    with pytest.raises(ValueError, match="max_failure_rate"):
        WindowConfig.from_dict({"max_failure_rate": 1.5})


# ---------------------------------------------------------------------------
# WindowBreached
# ---------------------------------------------------------------------------

def test_window_breached_str():
    exc = WindowBreached(0.75, 0.5)
    assert "75%" in str(exc)
    assert "50%" in str(exc)


# ---------------------------------------------------------------------------
# WindowTracker
# ---------------------------------------------------------------------------

def _tracker(enabled=True, window=60.0, min_attempts=3, max_rate=0.5):
    cfg = WindowConfig(
        enabled=enabled,
        window_seconds=window,
        min_attempts=min_attempts,
        max_failure_rate=max_rate,
    )
    return WindowTracker(config=cfg)


def test_disabled_tracker_never_raises():
    t = _tracker(enabled=False)
    for _ in range(10):
        t.record(failed=True, now=0.0)
    t.check(now=0.0)  # should not raise


def test_below_min_attempts_does_not_raise():
    t = _tracker(min_attempts=5)
    for i in range(4):
        t.record(failed=True, now=float(i))
    t.check(now=4.0)  # only 4 recorded, threshold not evaluated


def test_raises_when_failure_rate_exceeded():
    t = _tracker(max_rate=0.5, min_attempts=2)
    t.record(failed=True, now=1.0)
    t.record(failed=True, now=2.0)
    with pytest.raises(WindowBreached) as exc_info:
        t.check(now=3.0)
    assert exc_info.value.rate == 1.0


def test_does_not_raise_when_rate_acceptable():
    t = _tracker(max_rate=0.5, min_attempts=2)
    t.record(failed=False, now=1.0)
    t.record(failed=True, now=2.0)
    t.check(now=3.0)  # rate == 0.5, not strictly greater


def test_evicts_old_entries():
    t = _tracker(window=10.0, max_rate=0.5, min_attempts=2)
    # Old failures outside the window
    t.record(failed=True, now=0.0)
    t.record(failed=True, now=1.0)
    # Recent successes inside window
    t.record(failed=False, now=55.0)
    t.record(failed=False, now=56.0)
    t.check(now=60.0)  # old failures evicted, rate == 0.0


def test_failure_rate_property_none_when_empty():
    t = _tracker()
    assert t.failure_rate is None


def test_failure_rate_property_correct():
    t = _tracker()
    t.record(failed=True, now=1.0)
    t.record(failed=False, now=2.0)
    assert t.failure_rate == pytest.approx(0.5)
