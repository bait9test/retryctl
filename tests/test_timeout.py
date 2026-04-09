"""Tests for timeout module."""

import time
import pytest
from retryctl.timeout import TimeoutConfig, TimeoutTracker


def test_config_disabled_by_default():
    cfg = TimeoutConfig()
    assert cfg.enabled is False
    assert cfg.max_seconds is None
    assert cfg.per_attempt is True


def test_config_from_dict_empty():
    cfg = TimeoutConfig.from_dict({})
    assert cfg.enabled is False
    assert cfg.max_seconds is None


def test_config_from_dict_with_max_seconds():
    cfg = TimeoutConfig.from_dict({"max_seconds": 30})
    assert cfg.enabled is True
    assert cfg.max_seconds == 30
    assert cfg.per_attempt is True


def test_config_from_dict_total_timeout():
    cfg = TimeoutConfig.from_dict({
        "max_seconds": 60,
        "per_attempt": False
    })
    assert cfg.enabled is True
    assert cfg.max_seconds == 60
    assert cfg.per_attempt is False


def test_config_from_dict_zero_disables():
    cfg = TimeoutConfig.from_dict({"max_seconds": 0})
    assert cfg.enabled is False


def test_tracker_disabled_never_exceeds():
    cfg = TimeoutConfig(enabled=False)
    tracker = TimeoutTracker(cfg)
    tracker.start_run()
    tracker.start_attempt()
    time.sleep(0.01)
    assert tracker.is_exceeded() is False


def test_tracker_per_attempt_not_exceeded():
    cfg = TimeoutConfig(enabled=True, max_seconds=10, per_attempt=True)
    tracker = TimeoutTracker(cfg)
    tracker.start_run()
    tracker.start_attempt()
    time.sleep(0.01)
    assert tracker.is_exceeded() is False


def test_tracker_per_attempt_exceeded():
    cfg = TimeoutConfig(enabled=True, max_seconds=0, per_attempt=True)
    tracker = TimeoutTracker(cfg)
    tracker.start_run()
    tracker.start_attempt()
    time.sleep(0.02)
    assert tracker.is_exceeded() is True


def test_tracker_total_timeout_not_exceeded():
    cfg = TimeoutConfig(enabled=True, max_seconds=10, per_attempt=False)
    tracker = TimeoutTracker(cfg)
    tracker.start_run()
    tracker.start_attempt()
    time.sleep(0.01)
    assert tracker.is_exceeded() is False


def test_tracker_total_timeout_exceeded():
    cfg = TimeoutConfig(enabled=True, max_seconds=0, per_attempt=False)
    tracker = TimeoutTracker(cfg)
    tracker.start_run()
    time.sleep(0.02)
    tracker.start_attempt()
    assert tracker.is_exceeded() is True


def test_remaining_seconds_disabled_returns_none():
    cfg = TimeoutConfig(enabled=False)
    tracker = TimeoutTracker(cfg)
    tracker.start_run()
    tracker.start_attempt()
    assert tracker.remaining_seconds() is None


def test_remaining_seconds_per_attempt():
    cfg = TimeoutConfig(enabled=True, max_seconds=10, per_attempt=True)
    tracker = TimeoutTracker(cfg)
    tracker.start_run()
    tracker.start_attempt()
    time.sleep(0.01)
    remaining = tracker.remaining_seconds()
    assert remaining is not None
    assert 9.0 < remaining < 10.0


def test_remaining_seconds_total_timeout():
    cfg = TimeoutConfig(enabled=True, max_seconds=10, per_attempt=False)
    tracker = TimeoutTracker(cfg)
    tracker.start_run()
    time.sleep(0.01)
    tracker.start_attempt()
    remaining = tracker.remaining_seconds()
    assert remaining is not None
    assert 9.0 < remaining < 10.0


def test_remaining_seconds_never_negative():
    cfg = TimeoutConfig(enabled=True, max_seconds=0, per_attempt=True)
    tracker = TimeoutTracker(cfg)
    tracker.start_run()
    tracker.start_attempt()
    time.sleep(0.01)
    remaining = tracker.remaining_seconds()
    assert remaining == 0.0
