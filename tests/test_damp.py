"""Tests for retryctl/damp.py and retryctl/damp_middleware.py."""
from __future__ import annotations

import time
import pytest

from retryctl.damp import DampConfig, DampTracker, DampedAttempt
from retryctl.damp_middleware import (
    parse_damp,
    damp_config_to_dict,
    make_tracker,
    on_attempt_failure,
    on_run_success,
    describe_damp,
)


# ---------------------------------------------------------------------------
# DampConfig
# ---------------------------------------------------------------------------

def test_config_defaults():
    cfg = DampConfig()
    assert cfg.enabled is False
    assert cfg.threshold == 3
    assert cfg.window_seconds == 60.0
    assert cfg.fingerprint_stderr is True


def test_from_dict_full():
    cfg = DampConfig.from_dict(
        {"enabled": True, "threshold": 5, "window_seconds": 30.0, "fingerprint_stderr": False}
    )
    assert cfg.enabled is True
    assert cfg.threshold == 5
    assert cfg.window_seconds == 30.0
    assert cfg.fingerprint_stderr is False


def test_from_dict_empty_uses_defaults():
    cfg = DampConfig.from_dict({})
    assert cfg.enabled is False
    assert cfg.threshold == 3


def test_from_dict_auto_enables_when_threshold_set():
    cfg = DampConfig.from_dict({"threshold": 2})
    assert cfg.enabled is True


def test_from_dict_invalid_type_raises():
    with pytest.raises(TypeError):
        DampConfig.from_dict("not-a-dict")


def test_config_zero_threshold_raises():
    with pytest.raises(ValueError):
        DampConfig(threshold=0)


def test_config_negative_window_raises():
    with pytest.raises(ValueError):
        DampConfig(window_seconds=-1.0)


# ---------------------------------------------------------------------------
# DampTracker
# ---------------------------------------------------------------------------

def test_disabled_tracker_never_raises():
    cfg = DampConfig(enabled=False, threshold=1)
    tracker = DampTracker(cfg)
    for _ in range(10):
        tracker.record_failure(1, "boom")  # should not raise


def test_below_threshold_does_not_raise():
    cfg = DampConfig(enabled=True, threshold=3, window_seconds=60.0)
    tracker = DampTracker(cfg)
    tracker.record_failure(1, "err")
    tracker.record_failure(1, "err")
    tracker.record_failure(1, "err")  # exactly threshold – still ok


def test_exceeds_threshold_raises():
    cfg = DampConfig(enabled=True, threshold=3, window_seconds=60.0)
    tracker = DampTracker(cfg)
    for _ in range(3):
        tracker.record_failure(1, "err")
    with pytest.raises(DampedAttempt):
        tracker.record_failure(1, "err")


def test_different_exit_codes_tracked_separately():
    cfg = DampConfig(enabled=True, threshold=2, window_seconds=60.0)
    tracker = DampTracker(cfg)
    tracker.record_failure(1, "err")
    tracker.record_failure(1, "err")  # threshold reached for code 1
    # code 2 bucket is empty – should not raise
    tracker.record_failure(2, "err")


def test_success_resets_buckets():
    cfg = DampConfig(enabled=True, threshold=2, window_seconds=60.0)
    tracker = DampTracker(cfg)
    tracker.record_failure(1, "err")
    tracker.record_failure(1, "err")
    tracker.record_success()
    # After reset the counter is gone – should not raise
    tracker.record_failure(1, "err")
    tracker.record_failure(1, "err")


def test_window_expiry_evicts_old_timestamps(monkeypatch):
    cfg = DampConfig(enabled=True, threshold=2, window_seconds=1.0)
    tracker = DampTracker(cfg)
    tracker.record_failure(1, "err")
    tracker.record_failure(1, "err")
    # advance monotonic clock by 2 s so old entries are evicted
    original = time.monotonic
    monkeypatch.setattr(time, "monotonic", lambda: original() + 2.0)
    # bucket should be evicted – no raise
    tracker.record_failure(1, "err")


def test_damped_attempt_message():
    exc = DampedAttempt("1:abc", 4)
    assert "1:abc" in str(exc)
    assert "4" in str(exc)


# ---------------------------------------------------------------------------
# Middleware helpers
# ---------------------------------------------------------------------------

def test_parse_damp_missing_section_uses_defaults():
    cfg = parse_damp({})
    assert cfg.enabled is False


def test_parse_damp_full_section():
    cfg = parse_damp({"damp": {"enabled": True, "threshold": 4, "window_seconds": 20.0}})
    assert cfg.enabled is True
    assert cfg.threshold == 4


def test_damp_config_to_dict_roundtrip():
    cfg = DampConfig(enabled=True, threshold=5, window_seconds=45.0, fingerprint_stderr=False)
    d = damp_config_to_dict(cfg)
    cfg2 = DampConfig.from_dict(d)
    assert cfg2.threshold == 5
    assert cfg2.window_seconds == 45.0
    assert cfg2.fingerprint_stderr is False


def test_on_attempt_failure_delegates():
    cfg = DampConfig(enabled=True, threshold=1, window_seconds=60.0)
    tracker = make_tracker(cfg)
    on_attempt_failure(tracker, 1, "oops")
    with pytest.raises(DampedAttempt):
        on_attempt_failure(tracker, 1, "oops")


def test_on_run_success_clears():
    cfg = DampConfig(enabled=True, threshold=1, window_seconds=60.0)
    tracker = make_tracker(cfg)
    on_attempt_failure(tracker, 1, "oops")
    on_run_success(tracker)
    on_attempt_failure(tracker, 1, "oops")  # should not raise after reset


def test_describe_damp_disabled():
    assert "disabled" in describe_damp(DampConfig())


def test_describe_damp_enabled():
    cfg = DampConfig(enabled=True, threshold=3, window_seconds=30.0)
    desc = describe_damp(cfg)
    assert "3" in desc
    assert "30" in desc
