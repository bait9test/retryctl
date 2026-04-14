"""Tests for retryctl/flux.py"""
from __future__ import annotations

import pytest
from retryctl.flux import FluxConfig, FluxExceeded, FluxTracker


# ---------------------------------------------------------------------------
# Config tests
# ---------------------------------------------------------------------------

def test_config_defaults():
    cfg = FluxConfig()
    assert cfg.enabled is False
    assert cfg.window_seconds == 60.0
    assert cfg.threshold == 0.5
    assert cfg.min_samples == 3


def test_from_dict_empty_uses_defaults():
    cfg = FluxConfig.from_dict({})
    assert cfg.enabled is False


def test_from_dict_full():
    cfg = FluxConfig.from_dict({"flux": {"enabled": True, "window_seconds": 30.0, "threshold": 1.0, "min_samples": 2}})
    assert cfg.enabled is True
    assert cfg.window_seconds == 30.0
    assert cfg.threshold == 1.0
    assert cfg.min_samples == 2


def test_from_dict_invalid_type_raises():
    with pytest.raises(TypeError):
        FluxConfig.from_dict("bad")


def test_from_dict_invalid_section_type_raises():
    with pytest.raises(TypeError):
        FluxConfig.from_dict({"flux": "bad"})


def test_from_dict_zero_window_raises():
    with pytest.raises(ValueError):
        FluxConfig.from_dict({"flux": {"window_seconds": 0}})


def test_from_dict_negative_threshold_raises():
    with pytest.raises(ValueError):
        FluxConfig.from_dict({"flux": {"threshold": -1.0}})


def test_from_dict_zero_min_samples_raises():
    with pytest.raises(ValueError):
        FluxConfig.from_dict({"flux": {"min_samples": 0}})


# ---------------------------------------------------------------------------
# Tracker tests
# ---------------------------------------------------------------------------

def _tracker(enabled=True, window=10.0, threshold=0.5, min_samples=2):
    cfg = FluxConfig(enabled=enabled, window_seconds=window, threshold=threshold, min_samples=min_samples)
    return FluxTracker(config=cfg)


def test_disabled_tracker_never_raises():
    t = _tracker(enabled=False)
    for i in range(100):
        t.record_failure(now=float(i))
    t.check(now=100.0)  # should not raise


def test_below_min_samples_never_raises():
    t = _tracker(min_samples=5)
    for i in range(4):
        t.record_failure(now=float(i))
    t.check(now=4.0)  # only 4 samples, threshold not evaluated


def test_rate_below_threshold_does_not_raise():
    # window=10, threshold=1.0 → need >10 failures in 10 s
    t = _tracker(window=10.0, threshold=1.0, min_samples=2)
    # 3 failures spread over 10 s → rate=0.3 < 1.0
    for i in range(3):
        t.record_failure(now=float(i * 3))
    t.check(now=9.0)


def test_rate_above_threshold_raises():
    # window=10, threshold=0.5 → >5 failures in 10 s triggers
    t = _tracker(window=10.0, threshold=0.5, min_samples=2)
    for i in range(8):
        t.record_failure(now=float(i))
    with pytest.raises(FluxExceeded) as exc_info:
        t.check(now=9.0)
    assert exc_info.value.rate > 0.5
    assert exc_info.value.threshold == 0.5


def test_eviction_removes_old_timestamps():
    t = _tracker(window=5.0, threshold=0.5, min_samples=2)
    # add failures at t=0..4, then check at t=10 (all expired)
    for i in range(5):
        t.record_failure(now=float(i))
    t.check(now=10.0)  # window expired, no samples → no raise


def test_reset_clears_state():
    t = _tracker(window=10.0, threshold=0.5, min_samples=2)
    for i in range(10):
        t.record_failure(now=float(i))
    t.reset()
    t.check(now=10.0)  # no samples after reset


def test_flux_exceeded_str_contains_rate():
    exc = FluxExceeded(rate=1.234, threshold=0.5)
    assert "1.234" in str(exc)
    assert "0.500" in str(exc)
