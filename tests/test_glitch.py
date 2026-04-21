"""Tests for retryctl.glitch."""
from __future__ import annotations

import pytest

from retryctl.glitch import GlitchAbsorbed, GlitchConfig, GlitchTracker


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def test_config_defaults():
    cfg = GlitchConfig()
    assert cfg.enabled is False
    assert cfg.threshold == 2
    assert cfg.reset_on_success is True


def test_from_dict_full():
    cfg = GlitchConfig.from_dict({"enabled": True, "threshold": 3, "reset_on_success": False})
    assert cfg.enabled is True
    assert cfg.threshold == 3
    assert cfg.reset_on_success is False


def test_from_dict_empty_uses_defaults():
    cfg = GlitchConfig.from_dict({})
    assert cfg.threshold == 2
    assert cfg.reset_on_success is True


def test_from_dict_auto_enables_when_threshold_positive():
    cfg = GlitchConfig.from_dict({"threshold": 1})
    assert cfg.enabled is True


def test_from_dict_invalid_type_raises():
    with pytest.raises(TypeError):
        GlitchConfig.from_dict("bad")


def test_config_zero_threshold_raises():
    with pytest.raises(ValueError):
        GlitchConfig(enabled=True, threshold=0)


def test_config_negative_threshold_raises():
    with pytest.raises(ValueError):
        GlitchConfig(enabled=True, threshold=-1)


# ---------------------------------------------------------------------------
# Tracker — disabled
# ---------------------------------------------------------------------------

def test_disabled_tracker_never_absorbs():
    cfg = GlitchConfig(enabled=False, threshold=5)
    tracker = GlitchTracker(config=cfg)
    # Should not raise even after many failures
    for _ in range(10):
        tracker.on_attempt_failure()  # no exception
    assert tracker.consecutive == 10


# ---------------------------------------------------------------------------
# Tracker — enabled, within threshold
# ---------------------------------------------------------------------------

def test_first_failure_absorbed():
    cfg = GlitchConfig(enabled=True, threshold=2)
    tracker = GlitchTracker(config=cfg)
    with pytest.raises(GlitchAbsorbed) as exc_info:
        tracker.on_attempt_failure()
    assert exc_info.value.consecutive == 1
    assert exc_info.value.threshold == 2


def test_second_failure_absorbed_at_threshold():
    cfg = GlitchConfig(enabled=True, threshold=2)
    tracker = GlitchTracker(config=cfg)
    with pytest.raises(GlitchAbsorbed):
        tracker.on_attempt_failure()
    with pytest.raises(GlitchAbsorbed):
        tracker.on_attempt_failure()


def test_third_failure_escalates_beyond_threshold():
    cfg = GlitchConfig(enabled=True, threshold=2)
    tracker = GlitchTracker(config=cfg)
    # absorb first two
    for _ in range(2):
        try:
            tracker.on_attempt_failure()
        except GlitchAbsorbed:
            pass
    # third should NOT raise GlitchAbsorbed
    tracker.on_attempt_failure()
    assert tracker.consecutive == 3


# ---------------------------------------------------------------------------
# Tracker — reset on success
# ---------------------------------------------------------------------------

def test_success_resets_counter():
    cfg = GlitchConfig(enabled=True, threshold=3, reset_on_success=True)
    tracker = GlitchTracker(config=cfg)
    for _ in range(2):
        try:
            tracker.on_attempt_failure()
        except GlitchAbsorbed:
            pass
    tracker.on_run_success()
    assert tracker.consecutive == 0


def test_success_does_not_reset_when_disabled():
    cfg = GlitchConfig(enabled=True, threshold=3, reset_on_success=False)
    tracker = GlitchTracker(config=cfg)
    for _ in range(2):
        try:
            tracker.on_attempt_failure()
        except GlitchAbsorbed:
            pass
    tracker.on_run_success()
    assert tracker.consecutive == 2


def test_glitch_absorbed_str_contains_info():
    exc = GlitchAbsorbed(consecutive=1, threshold=3)
    assert "1" in str(exc)
    assert "3" in str(exc)
