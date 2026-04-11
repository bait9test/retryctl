"""Tests for retryctl.drift."""
from __future__ import annotations

import pytest
from unittest.mock import patch, call

from retryctl.drift import DriftConfig, DriftExceeded, sleep_with_drift_check, _pct


# ---------------------------------------------------------------------------
# DriftConfig
# ---------------------------------------------------------------------------

def test_config_defaults():
    cfg = DriftConfig()
    assert cfg.enabled is False
    assert cfg.warn_threshold == 0.2
    assert cfg.abort_threshold is None


def test_config_from_dict_empty():
    cfg = DriftConfig.from_dict({})
    assert cfg.enabled is False
    assert cfg.warn_threshold == 0.2
    assert cfg.abort_threshold is None


def test_config_from_dict_full():
    cfg = DriftConfig.from_dict({"enabled": True, "warn_threshold": 0.1, "abort_threshold": 0.5})
    assert cfg.enabled is True
    assert cfg.warn_threshold == pytest.approx(0.1)
    assert cfg.abort_threshold == pytest.approx(0.5)


def test_config_from_dict_invalid_type_raises():
    with pytest.raises(TypeError):
        DriftConfig.from_dict("not a dict")  # type: ignore


def test_config_negative_warn_raises():
    with pytest.raises(ValueError, match="warn_threshold"):
        DriftConfig.from_dict({"warn_threshold": -0.1})


def test_config_negative_abort_raises():
    with pytest.raises(ValueError, match="abort_threshold"):
        DriftConfig.from_dict({"abort_threshold": -1})


# ---------------------------------------------------------------------------
# _pct helper
# ---------------------------------------------------------------------------

def test_pct_zero_expected():
    assert _pct(0, 5) == 0.0


def test_pct_normal():
    assert _pct(1.0, 1.5) == pytest.approx(50.0)


# ---------------------------------------------------------------------------
# sleep_with_drift_check
# ---------------------------------------------------------------------------

def _make_sleep_mock(actual_elapsed: float):
    """Return a mock for time.sleep and time.monotonic that simulates elapsed time."""
    calls = [0.0, actual_elapsed]  # first call returns 0.0, second returns elapsed
    monotonic_iter = iter(calls)

    def fake_monotonic():
        return next(monotonic_iter)

    return fake_monotonic


def test_disabled_config_skips_checks():
    cfg = DriftConfig(enabled=False, warn_threshold=0.0, abort_threshold=0.0)
    with patch("time.sleep"), patch("time.monotonic", side_effect=[0.0, 999.0]):
        elapsed = sleep_with_drift_check(1.0, cfg)
    assert elapsed == pytest.approx(999.0)


def test_no_drift_no_warning(caplog):
    cfg = DriftConfig(enabled=True, warn_threshold=0.2)
    with patch("time.sleep"), patch("time.monotonic", side_effect=[0.0, 1.05]):
        with caplog.at_level("WARNING"):
            sleep_with_drift_check(1.0, cfg)
    assert "drift" not in caplog.text.lower()


def test_drift_above_warn_logs_warning(caplog):
    cfg = DriftConfig(enabled=True, warn_threshold=0.1)
    # expected=1.0, actual=1.5 => 50% drift > 10% threshold
    with patch("time.sleep"), patch("time.monotonic", side_effect=[0.0, 1.5]):
        with caplog.at_level("WARNING"):
            sleep_with_drift_check(1.0, cfg)
    assert "drift" in caplog.text.lower()


def test_drift_above_abort_raises():
    cfg = DriftConfig(enabled=True, warn_threshold=0.1, abort_threshold=0.3)
    # expected=1.0, actual=1.5 => 50% drift > 30% abort threshold
    with patch("time.sleep"), patch("time.monotonic", side_effect=[0.0, 1.5]):
        with pytest.raises(DriftExceeded) as exc_info:
            sleep_with_drift_check(1.0, cfg)
    err = exc_info.value
    assert err.expected == pytest.approx(1.0)
    assert err.actual == pytest.approx(1.5)
    assert err.threshold == pytest.approx(0.3)
    assert "abort" in str(err).lower()


def test_zero_expected_no_drift_check():
    cfg = DriftConfig(enabled=True, warn_threshold=0.0, abort_threshold=0.0)
    with patch("time.sleep"), patch("time.monotonic", side_effect=[0.0, 5.0]):
        elapsed = sleep_with_drift_check(0.0, cfg)
    assert elapsed == pytest.approx(5.0)
