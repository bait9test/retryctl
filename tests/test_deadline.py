"""Tests for retryctl/deadline.py."""
from __future__ import annotations

import time
from unittest.mock import patch

import pytest

from retryctl.deadline import DeadlineConfig, DeadlineExceeded, DeadlineTracker


# ---------------------------------------------------------------------------
# DeadlineConfig
# ---------------------------------------------------------------------------

def test_config_defaults():
    cfg = DeadlineConfig()
    assert cfg.per_attempt_seconds is None
    assert cfg.total_seconds is None
    assert cfg.enabled is False


def test_config_from_dict_empty():
    cfg = DeadlineConfig.from_dict({})
    assert not cfg.enabled


def test_config_from_dict_per_attempt():
    cfg = DeadlineConfig.from_dict({"per_attempt_seconds": 5})
    assert cfg.per_attempt_seconds == 5.0
    assert cfg.total_seconds is None
    assert cfg.enabled is True


def test_config_from_dict_total():
    cfg = DeadlineConfig.from_dict({"total_seconds": 30})
    assert cfg.total_seconds == 30.0
    assert cfg.per_attempt_seconds is None
    assert cfg.enabled is True


def test_config_from_dict_both():
    cfg = DeadlineConfig.from_dict({"per_attempt_seconds": 3, "total_seconds": 20})
    assert cfg.per_attempt_seconds == 3.0
    assert cfg.total_seconds == 20.0
    assert cfg.enabled is True


def test_config_from_dict_zero_per_attempt_raises():
    with pytest.raises(ValueError, match="per_attempt_seconds must be positive"):
        DeadlineConfig.from_dict({"per_attempt_seconds": 0})


def test_config_from_dict_negative_total_raises():
    with pytest.raises(ValueError, match="total_seconds must be positive"):
        DeadlineConfig.from_dict({"total_seconds": -1})


# ---------------------------------------------------------------------------
# DeadlineExceeded
# ---------------------------------------------------------------------------

def test_deadline_exceeded_message():
    exc = DeadlineExceeded("per_attempt", 5.0)
    assert "per_attempt" in str(exc)
    assert "5.0" in str(exc)
    assert exc.kind == "per_attempt"
    assert exc.limit == 5.0


# ---------------------------------------------------------------------------
# DeadlineTracker — disabled
# ---------------------------------------------------------------------------

def test_disabled_tracker_check_attempt_does_nothing():
    cfg = DeadlineConfig()
    tracker = DeadlineTracker(config=cfg)
    start = tracker.attempt_start()
    tracker.check_attempt(start)  # must not raise


def test_disabled_tracker_check_total_does_nothing():
    cfg = DeadlineConfig()
    tracker = DeadlineTracker(config=cfg)
    tracker.check_total()  # must not raise


def test_disabled_remaining_returns_none():
    cfg = DeadlineConfig()
    tracker = DeadlineTracker(config=cfg)
    start = tracker.attempt_start()
    assert tracker.remaining_attempt_seconds(start) is None
    assert tracker.remaining_total_seconds() is None


# ---------------------------------------------------------------------------
# DeadlineTracker — per-attempt enforcement
# ---------------------------------------------------------------------------

def test_check_attempt_within_limit_does_not_raise():
    cfg = DeadlineConfig(per_attempt_seconds=60.0)
    tracker = DeadlineTracker(config=cfg)
    start = time.monotonic()
    tracker.check_attempt(start)  # well within limit


def test_check_attempt_exceeded_raises():
    cfg = DeadlineConfig(per_attempt_seconds=1.0)
    tracker = DeadlineTracker(config=cfg)
    # fake an attempt that started 2 seconds ago
    past = time.monotonic() - 2.0
    with pytest.raises(DeadlineExceeded) as exc_info:
        tracker.check_attempt(past)
    assert exc_info.value.kind == "per_attempt"


def test_remaining_attempt_seconds_positive():
    cfg = DeadlineConfig(per_attempt_seconds=60.0)
    tracker = DeadlineTracker(config=cfg)
    start = time.monotonic()
    remaining = tracker.remaining_attempt_seconds(start)
    assert remaining is not None
    assert 0 < remaining <= 60.0


def test_remaining_attempt_seconds_clamps_to_zero():
    cfg = DeadlineConfig(per_attempt_seconds=1.0)
    tracker = DeadlineTracker(config=cfg)
    past = time.monotonic() - 5.0
    assert tracker.remaining_attempt_seconds(past) == 0.0


# ---------------------------------------------------------------------------
# DeadlineTracker — total enforcement
# ---------------------------------------------------------------------------

def test_check_total_exceeded_raises():
    cfg = DeadlineConfig(total_seconds=1.0)
    tracker = DeadlineTracker(config=cfg)
    # wind back the run start
    tracker._run_start = time.monotonic() - 2.0
    with pytest.raises(DeadlineExceeded) as exc_info:
        tracker.check_total()
    assert exc_info.value.kind == "total"


def test_remaining_total_seconds_clamps_to_zero():
    cfg = DeadlineConfig(total_seconds=5.0)
    tracker = DeadlineTracker(config=cfg)
    tracker._run_start = time.monotonic() - 10.0
    assert tracker.remaining_total_seconds() == 0.0
