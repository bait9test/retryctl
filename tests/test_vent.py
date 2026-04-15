"""Tests for retryctl.vent and retryctl.vent_middleware."""
from __future__ import annotations

import time
import pytest

from retryctl.vent import VentConfig, VentOpen, VentTracker
from retryctl.vent_middleware import (
    parse_vent,
    vent_config_to_dict,
    make_tracker,
    on_attempt_failure,
    on_run_success,
    before_attempt,
    describe_vent,
)


# ---------------------------------------------------------------------------
# VentConfig
# ---------------------------------------------------------------------------

def test_config_defaults():
    cfg = VentConfig()
    assert cfg.enabled is False
    assert cfg.threshold == 0.75
    assert cfg.window == 10
    assert cfg.cooldown_seconds == 30.0


def test_from_dict_full():
    cfg = VentConfig.from_dict({"enabled": True, "threshold": 0.5, "window": 5, "cooldown_seconds": 10.0})
    assert cfg.enabled is True
    assert cfg.threshold == 0.5
    assert cfg.window == 5
    assert cfg.cooldown_seconds == 10.0


def test_from_dict_empty_uses_defaults():
    cfg = VentConfig.from_dict({})
    assert cfg.threshold == 0.75
    assert cfg.window == 10


def test_from_dict_auto_enables_when_threshold_set():
    cfg = VentConfig.from_dict({"threshold": 0.6})
    assert cfg.enabled is True


def test_from_dict_invalid_type_raises():
    with pytest.raises(TypeError):
        VentConfig.from_dict("bad")


def test_from_dict_zero_threshold_raises():
    with pytest.raises(ValueError):
        VentConfig.from_dict({"threshold": 0.0})


def test_from_dict_threshold_above_one_raises():
    with pytest.raises(ValueError):
        VentConfig.from_dict({"threshold": 1.1})


def test_from_dict_zero_window_raises():
    with pytest.raises(ValueError):
        VentConfig.from_dict({"window": 0})


def test_from_dict_negative_cooldown_raises():
    with pytest.raises(ValueError):
        VentConfig.from_dict({"cooldown_seconds": -1})


# ---------------------------------------------------------------------------
# VentTracker
# ---------------------------------------------------------------------------

def _make_tracker(threshold=0.5, window=4, cooldown=0.05) -> VentTracker:
    cfg = VentConfig(enabled=True, threshold=threshold, window=window, cooldown_seconds=cooldown)
    return VentTracker(config=cfg)


def test_disabled_tracker_never_raises():
    cfg = VentConfig(enabled=False)
    tracker = VentTracker(config=cfg)
    for _ in range(20):
        tracker.record_failure()
    tracker.check()  # should not raise


def test_below_threshold_does_not_open():
    tracker = _make_tracker(threshold=0.75, window=4)
    tracker.record_failure()
    tracker.record_success()
    tracker.record_success()
    tracker.record_success()
    tracker.check()  # 1/4 = 25% < 75%


def test_at_threshold_opens_vent():
    tracker = _make_tracker(threshold=0.5, window=4, cooldown=60)
    tracker.record_failure()
    tracker.record_failure()
    tracker.record_success()
    tracker.record_success()
    with pytest.raises(VentOpen) as exc_info:
        tracker.check()
    assert exc_info.value.rate == 0.5


def test_window_evicts_old_entries():
    tracker = _make_tracker(threshold=0.75, window=4)
    # push 4 failures then 4 successes – old failures fall off
    for _ in range(4):
        tracker.record_failure()
    for _ in range(4):
        tracker.record_success()
    # window now has 4 successes: rate = 0 < 0.75
    tracker.check()


def test_cooldown_holds_vent_open():
    tracker = _make_tracker(threshold=0.5, window=2, cooldown=60)
    tracker.record_failure()
    tracker.record_failure()
    with pytest.raises(VentOpen):
        tracker.check()
    # even after adding a success the vent stays open during cooldown
    tracker.record_success()
    with pytest.raises(VentOpen):
        tracker.check()


def test_vent_closes_after_cooldown(monkeypatch):
    now = [time.monotonic()]
    monkeypatch.setattr("retryctl.vent.time.monotonic", lambda: now[0])
    tracker = _make_tracker(threshold=0.5, window=2, cooldown=5)
    tracker.record_failure()
    tracker.record_failure()
    with pytest.raises(VentOpen):
        tracker.check()
    now[0] += 10  # advance past cooldown
    tracker.record_success()
    tracker.record_success()
    tracker.check()  # should not raise


# ---------------------------------------------------------------------------
# Middleware helpers
# ---------------------------------------------------------------------------

def test_parse_vent_missing_section_uses_defaults():
    cfg = parse_vent({})
    assert cfg.enabled is False


def test_parse_vent_full_section():
    cfg = parse_vent({"vent": {"enabled": True, "threshold": 0.6, "window": 8}})
    assert cfg.enabled is True
    assert cfg.threshold == 0.6


def test_parse_vent_invalid_type_raises():
    with pytest.raises(TypeError):
        parse_vent({"vent": "bad"})


def test_vent_config_to_dict_roundtrip():
    cfg = VentConfig(enabled=True, threshold=0.8, window=6, cooldown_seconds=15.0)
    d = vent_config_to_dict(cfg)
    assert d["threshold"] == 0.8
    assert d["window"] == 6
    assert VentConfig.from_dict(d).cooldown_seconds == 15.0


def test_middleware_helpers_call_tracker():
    cfg = VentConfig(enabled=True, threshold=0.5, window=2, cooldown_seconds=60)
    tracker = make_tracker(cfg)
    on_attempt_failure(tracker)
    on_attempt_failure(tracker)
    with pytest.raises(VentOpen):
        before_attempt(tracker)


def test_on_run_success_records_success():
    cfg = VentConfig(enabled=True, threshold=0.5, window=4)
    tracker = make_tracker(cfg)
    on_run_success(tracker)
    assert list(tracker._history) == [False]


def test_describe_vent_disabled():
    assert "disabled" in describe_vent(VentConfig(enabled=False))


def test_describe_vent_enabled():
    desc = describe_vent(VentConfig(enabled=True, threshold=0.6, window=5, cooldown_seconds=20))
    assert "60%" in desc
    assert "window=5" in desc
