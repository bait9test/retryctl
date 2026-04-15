"""Tests for retryctl/surge.py."""
import pytest
from retryctl.surge import SurgeConfig, SurgeDetected, SurgeTracker


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def test_config_defaults():
    cfg = SurgeConfig()
    assert cfg.enabled is False
    assert cfg.window_seconds == 60.0
    assert cfg.threshold == 5
    assert cfg.cooldown_seconds == 30.0


def test_from_dict_full():
    cfg = SurgeConfig.from_dict(
        {"enabled": True, "window_seconds": 10.0, "threshold": 3, "cooldown_seconds": 5.0}
    )
    assert cfg.enabled is True
    assert cfg.window_seconds == 10.0
    assert cfg.threshold == 3
    assert cfg.cooldown_seconds == 5.0


def test_from_dict_empty_uses_defaults():
    cfg = SurgeConfig.from_dict({})
    assert cfg.window_seconds == 60.0
    assert cfg.threshold == 5


def test_from_dict_auto_enables_when_threshold_set():
    cfg = SurgeConfig.from_dict({"threshold": 2})
    assert cfg.enabled is True


def test_from_dict_invalid_type_raises():
    with pytest.raises(TypeError):
        SurgeConfig.from_dict("not a dict")  # type: ignore


def test_from_dict_zero_window_raises():
    with pytest.raises(ValueError, match="window_seconds"):
        SurgeConfig.from_dict({"window_seconds": 0})


def test_from_dict_zero_threshold_raises():
    with pytest.raises(ValueError, match="threshold"):
        SurgeConfig.from_dict({"threshold": 0})


def test_from_dict_negative_cooldown_raises():
    with pytest.raises(ValueError, match="cooldown_seconds"):
        SurgeConfig.from_dict({"cooldown_seconds": -1})


# ---------------------------------------------------------------------------
# Tracker
# ---------------------------------------------------------------------------

def _tracker(threshold: int = 3, window: float = 60.0, cooldown: float = 10.0) -> SurgeTracker:
    cfg = SurgeConfig(enabled=True, window_seconds=window, threshold=threshold, cooldown_seconds=cooldown)
    return SurgeTracker(config=cfg)


def test_disabled_tracker_never_raises():
    cfg = SurgeConfig(enabled=False, threshold=1)
    t = SurgeTracker(config=cfg)
    for _ in range(20):
        t.record_failure()  # should never raise


def test_below_threshold_does_not_raise():
    t = _tracker(threshold=3)
    t.record_failure(now=1.0)
    t.record_failure(now=2.0)
    assert t.failure_count == 2


def test_at_threshold_raises_surge_detected():
    t = _tracker(threshold=3, cooldown=15.0)
    t.record_failure(now=1.0)
    t.record_failure(now=2.0)
    with pytest.raises(SurgeDetected) as exc_info:
        t.record_failure(now=3.0)
    assert exc_info.value.cooldown == 15.0


def test_surge_detected_clears_window():
    t = _tracker(threshold=2)
    t.record_failure(now=1.0)
    with pytest.raises(SurgeDetected):
        t.record_failure(now=2.0)
    # after surge, counter resets
    assert t.failure_count == 0


def test_success_resets_counter():
    t = _tracker(threshold=3)
    t.record_failure(now=1.0)
    t.record_failure(now=2.0)
    t.record_success()
    assert t.failure_count == 0


def test_expired_failures_evicted():
    t = _tracker(threshold=3, window=5.0)
    t.record_failure(now=1.0)
    t.record_failure(now=2.0)
    # both older than window; should be evicted at now=10
    t.record_failure(now=10.0)
    assert t.failure_count == 1  # only the latest survives


def test_surge_detected_str_contains_cooldown():
    err = SurgeDetected(cooldown=42.0)
    assert "42.0" in str(err)
