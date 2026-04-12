"""Tests for retryctl.watermark and retryctl.watermark_middleware."""
from __future__ import annotations

import pytest

from retryctl.watermark import (
    WatermarkConfig,
    WatermarkTracker,
    WatermarkBreached,
)
from retryctl.watermark_middleware import (
    parse_watermark,
    watermark_config_to_dict,
    on_attempt_failure,
    on_run_success,
    describe_watermark,
)


# ---------------------------------------------------------------------------
# WatermarkConfig
# ---------------------------------------------------------------------------

def test_config_defaults():
    cfg = WatermarkConfig()
    assert cfg.enabled is False
    assert cfg.threshold == 3
    assert cfg.reset_on_success is True


def test_config_from_dict_full():
    cfg = WatermarkConfig.from_dict({"enabled": True, "threshold": 5, "reset_on_success": False})
    assert cfg.enabled is True
    assert cfg.threshold == 5
    assert cfg.reset_on_success is False


def test_config_from_dict_empty():
    cfg = WatermarkConfig.from_dict({})
    assert cfg.enabled is False
    assert cfg.threshold == 3


def test_config_from_dict_invalid_type_raises():
    with pytest.raises(TypeError):
        WatermarkConfig.from_dict("bad")


def test_config_zero_threshold_raises():
    with pytest.raises(ValueError):
        WatermarkConfig.from_dict({"threshold": 0})


def test_config_negative_threshold_raises():
    with pytest.raises(ValueError):
        WatermarkConfig.from_dict({"threshold": -1})


# ---------------------------------------------------------------------------
# WatermarkTracker
# ---------------------------------------------------------------------------

def test_disabled_tracker_never_raises():
    cfg = WatermarkConfig(enabled=False, threshold=1)
    tracker = WatermarkTracker(cfg)
    for _ in range(10):
        tracker.record_failure()  # should not raise
    assert tracker.consecutive == 0


def test_tracker_raises_at_threshold():
    cfg = WatermarkConfig(enabled=True, threshold=3)
    tracker = WatermarkTracker(cfg)
    tracker.record_failure()
    tracker.record_failure()
    with pytest.raises(WatermarkBreached) as exc_info:
        tracker.record_failure()
    assert exc_info.value.consecutive == 3
    assert exc_info.value.threshold == 3


def test_tracker_does_not_raise_below_threshold():
    cfg = WatermarkConfig(enabled=True, threshold=5)
    tracker = WatermarkTracker(cfg)
    for _ in range(4):
        tracker.record_failure()  # must not raise
    assert tracker.consecutive == 4


def test_success_resets_counter():
    cfg = WatermarkConfig(enabled=True, threshold=3, reset_on_success=True)
    tracker = WatermarkTracker(cfg)
    tracker.record_failure()
    tracker.record_failure()
    tracker.record_success()
    assert tracker.consecutive == 0


def test_success_no_reset_when_disabled():
    cfg = WatermarkConfig(enabled=True, threshold=5, reset_on_success=False)
    tracker = WatermarkTracker(cfg)
    tracker.record_failure()
    tracker.record_failure()
    tracker.record_success()
    assert tracker.consecutive == 2


def test_reset_clears_counter():
    cfg = WatermarkConfig(enabled=True, threshold=3)
    tracker = WatermarkTracker(cfg)
    tracker.record_failure()
    tracker.reset()
    assert tracker.consecutive == 0


def test_watermark_breached_str():
    exc = WatermarkBreached(consecutive=4, threshold=3)
    assert "4" in str(exc) and "3" in str(exc)


# ---------------------------------------------------------------------------
# Middleware helpers
# ---------------------------------------------------------------------------

def test_parse_watermark_empty_config():
    cfg = parse_watermark({})
    assert cfg.enabled is False


def test_parse_watermark_full_section():
    cfg = parse_watermark({"watermark": {"enabled": True, "threshold": 2}})
    assert cfg.enabled is True
    assert cfg.threshold == 2


def test_parse_watermark_invalid_type_raises():
    with pytest.raises(TypeError):
        parse_watermark({"watermark": "bad"})


def test_watermark_config_to_dict_roundtrip():
    cfg = WatermarkConfig(enabled=True, threshold=7, reset_on_success=False)
    d = watermark_config_to_dict(cfg)
    assert d == {"enabled": True, "threshold": 7, "reset_on_success": False}


def test_on_attempt_failure_raises_when_threshold_met():
    cfg = WatermarkConfig(enabled=True, threshold=2)
    tracker = WatermarkTracker(cfg)
    on_attempt_failure(tracker)
    with pytest.raises(WatermarkBreached):
        on_attempt_failure(tracker)


def test_on_run_success_resets():
    cfg = WatermarkConfig(enabled=True, threshold=3)
    tracker = WatermarkTracker(cfg)
    tracker.record_failure()
    on_run_success(tracker)
    assert tracker.consecutive == 0


def test_describe_watermark_disabled():
    cfg = WatermarkConfig(enabled=False)
    assert "disabled" in describe_watermark(cfg)


def test_describe_watermark_enabled():
    cfg = WatermarkConfig(enabled=True, threshold=4)
    desc = describe_watermark(cfg)
    assert "enabled" in desc and "4" in desc
