"""Tests for retryctl.pacing and retryctl.pacing_middleware."""
from __future__ import annotations

import time
import pytest

from retryctl.pacing import PacingConfig, PacingTracker
from retryctl.pacing_middleware import (
    parse_pacing,
    pacing_config_to_dict,
    before_attempt,
    on_run_complete,
    describe_pacing,
)


# ---------------------------------------------------------------------------
# PacingConfig
# ---------------------------------------------------------------------------

def test_config_defaults():
    cfg = PacingConfig()
    assert cfg.enabled is False
    assert cfg.min_interval_s == 1.0


def test_config_from_dict_full():
    cfg = PacingConfig.from_dict({"enabled": True, "min_interval_s": 2.5})
    assert cfg.enabled is True
    assert cfg.min_interval_s == 2.5


def test_config_from_dict_empty_uses_defaults():
    cfg = PacingConfig.from_dict({})
    assert cfg.enabled is False
    assert cfg.min_interval_s == 1.0


def test_config_auto_enables_when_interval_positive():
    cfg = PacingConfig.from_dict({"min_interval_s": 0.5})
    assert cfg.enabled is True


def test_config_negative_interval_raises():
    with pytest.raises(ValueError):
        PacingConfig(min_interval_s=-1.0)


def test_config_from_dict_invalid_type_raises():
    with pytest.raises(TypeError):
        PacingConfig.from_dict("bad")


# ---------------------------------------------------------------------------
# PacingTracker
# ---------------------------------------------------------------------------

def test_tracker_no_wait_when_disabled():
    cfg = PacingConfig(enabled=False, min_interval_s=10.0)
    tracker = PacingTracker(config=cfg)
    tracker.record_attempt_start()
    time.sleep(0.01)
    slept = tracker.wait_if_needed()
    assert slept == 0.0


def test_tracker_no_wait_on_first_call():
    cfg = PacingConfig(enabled=True, min_interval_s=1.0)
    tracker = PacingTracker(config=cfg)
    slept = tracker.wait_if_needed()
    assert slept == 0.0


def test_tracker_waits_when_too_fast(monkeypatch):
    calls = []
    monkeypatch.setattr("retryctl.pacing.time.sleep", lambda s: calls.append(s))
    # Fake monotonic so elapsed is 0 (instant attempt)
    now = [100.0]
    monkeypatch.setattr("retryctl.pacing.time.monotonic", lambda: now[0])

    cfg = PacingConfig(enabled=True, min_interval_s=1.0)
    tracker = PacingTracker(config=cfg)
    tracker.record_attempt_start()
    slept = tracker.wait_if_needed()
    assert slept == pytest.approx(1.0)
    assert calls == [1.0]


def test_tracker_no_wait_when_interval_elapsed(monkeypatch):
    now = [100.0]
    monkeypatch.setattr("retryctl.pacing.time.monotonic", lambda: now[0])
    monkeypatch.setattr("retryctl.pacing.time.sleep", lambda s: None)

    cfg = PacingConfig(enabled=True, min_interval_s=1.0)
    tracker = PacingTracker(config=cfg)
    tracker.record_attempt_start()
    now[0] = 102.0  # 2 s have passed — well beyond the 1 s floor
    slept = tracker.wait_if_needed()
    assert slept == 0.0


def test_tracker_reset_clears_last_time():
    cfg = PacingConfig(enabled=True, min_interval_s=1.0)
    tracker = PacingTracker(config=cfg)
    tracker.record_attempt_start()
    tracker.reset()
    assert tracker._last_attempt_time is None


# ---------------------------------------------------------------------------
# Middleware helpers
# ---------------------------------------------------------------------------

def test_parse_pacing_empty_config():
    cfg = parse_pacing({})
    assert isinstance(cfg, PacingConfig)
    assert cfg.enabled is False


def test_parse_pacing_full_section():
    cfg = parse_pacing({"pacing": {"enabled": True, "min_interval_s": 3.0}})
    assert cfg.enabled is True
    assert cfg.min_interval_s == 3.0


def test_parse_pacing_invalid_type_raises():
    with pytest.raises(TypeError):
        parse_pacing({"pacing": "oops"})


def test_pacing_config_to_dict_roundtrip():
    cfg = PacingConfig(enabled=True, min_interval_s=2.0)
    d = pacing_config_to_dict(cfg)
    assert d == {"enabled": True, "min_interval_s": 2.0}


def test_before_attempt_returns_slept(monkeypatch):
    monkeypatch.setattr("retryctl.pacing.time.sleep", lambda s: None)
    now = [100.0]
    monkeypatch.setattr("retryctl.pacing.time.monotonic", lambda: now[0])

    cfg = PacingConfig(enabled=True, min_interval_s=1.0)
    tracker = PacingTracker(config=cfg)
    tracker.record_attempt_start()  # sets last time to 100.0
    slept = before_attempt(tracker, attempt=2)
    assert slept == pytest.approx(1.0)


def test_on_run_complete_resets_tracker():
    cfg = PacingConfig(enabled=True, min_interval_s=1.0)
    tracker = PacingTracker(config=cfg)
    tracker.record_attempt_start()
    on_run_complete(tracker)
    assert tracker._last_attempt_time is None


def test_describe_pacing_disabled():
    assert describe_pacing(PacingConfig(enabled=False)) == "pacing disabled"


def test_describe_pacing_enabled():
    desc = describe_pacing(PacingConfig(enabled=True, min_interval_s=0.5))
    assert "0.5s" in desc
    assert "enabled" in desc
