"""Tests for retryctl.skew."""
import pytest
from retryctl.skew import SkewConfig, SkewExceeded, SkewTracker


# ---------------------------------------------------------------------------
# SkewConfig
# ---------------------------------------------------------------------------

def test_config_defaults():
    cfg = SkewConfig()
    assert cfg.enabled is False
    assert cfg.warn_pct == 50.0
    assert cfg.abort_pct == 0.0
    assert cfg.min_samples == 3


def test_from_dict_empty_uses_defaults():
    cfg = SkewConfig.from_dict({})
    assert cfg.warn_pct == 50.0
    assert cfg.abort_pct == 0.0
    assert cfg.min_samples == 3


def test_from_dict_full():
    cfg = SkewConfig.from_dict({"warn_pct": 30.0, "abort_pct": 200.0,
                                 "min_samples": 5, "enabled": True})
    assert cfg.warn_pct == 30.0
    assert cfg.abort_pct == 200.0
    assert cfg.min_samples == 5
    assert cfg.enabled is True


def test_from_dict_auto_enables_when_warn_pct_positive():
    cfg = SkewConfig.from_dict({"warn_pct": 25.0})
    assert cfg.enabled is True


def test_from_dict_auto_enables_when_abort_pct_positive():
    cfg = SkewConfig.from_dict({"abort_pct": 100.0})
    assert cfg.enabled is True


def test_from_dict_invalid_type_raises():
    with pytest.raises(TypeError):
        SkewConfig.from_dict("bad")


def test_from_dict_negative_warn_pct_raises():
    with pytest.raises(ValueError):
        SkewConfig.from_dict({"warn_pct": -1.0})


def test_from_dict_negative_abort_pct_raises():
    with pytest.raises(ValueError):
        SkewConfig.from_dict({"abort_pct": -5.0})


def test_from_dict_min_samples_zero_raises():
    with pytest.raises(ValueError):
        SkewConfig.from_dict({"min_samples": 0})


# ---------------------------------------------------------------------------
# SkewTracker
# ---------------------------------------------------------------------------

def _tracker(warn_pct=50.0, abort_pct=0.0, min_samples=3):
    cfg = SkewConfig(enabled=True, warn_pct=warn_pct,
                     abort_pct=abort_pct, min_samples=min_samples)
    return SkewTracker(config=cfg)


def test_disabled_tracker_never_raises():
    cfg = SkewConfig(enabled=False, warn_pct=1.0, abort_pct=1.0, min_samples=1)
    t = SkewTracker(config=cfg)
    for _ in range(5):
        t.record(0.001)  # should not raise


def test_no_evaluation_before_min_samples():
    t = _tracker(abort_pct=1.0, min_samples=4)
    # only 3 samples recorded — no abort even with huge deviation
    t.record(1.0)
    t.record(1.0)
    t.record(100.0)  # would trigger if min_samples reached


def test_warn_logged_on_deviation(caplog):
    import logging
    t = _tracker(warn_pct=20.0)
    t.record(1.0)
    t.record(1.0)
    with caplog.at_level(logging.WARNING, logger="retryctl.skew"):
        t.record(5.0)  # 400% deviation from mean of 1.0
    assert "skew detected" in caplog.text


def test_abort_raises_skew_exceeded():
    t = _tracker(warn_pct=10.0, abort_pct=50.0)
    t.record(1.0)
    t.record(1.0)
    with pytest.raises(SkewExceeded) as exc_info:
        t.record(5.0)
    assert exc_info.value.deviation_pct > 50.0


def test_skew_exceeded_str_contains_info():
    err = SkewExceeded(120.5, 1.0, 2.2)
    msg = str(err)
    assert "120.5" in msg
    assert "mean=1.000" in msg


def test_samples_stored():
    t = _tracker()
    t.record(1.0)
    t.record(2.0)
    assert t.samples == [1.0, 2.0]


def test_reset_clears_samples():
    t = _tracker()
    t.record(1.0)
    t.reset()
    assert t.samples == []


def test_no_abort_when_abort_pct_zero():
    # abort_pct=0 means disabled; even large deviation should not raise
    t = _tracker(warn_pct=5.0, abort_pct=0.0)
    t.record(1.0)
    t.record(1.0)
    t.record(999.0)  # huge — warns but does not raise
