"""Tests for retryctl.stagger and retryctl.stagger_middleware."""
from __future__ import annotations

import pytest
from unittest.mock import patch

from retryctl.stagger import (
    StaggerConfig,
    compute_stagger_delay,
    apply_stagger,
)
from retryctl.stagger_middleware import (
    parse_stagger,
    stagger_config_to_dict,
    maybe_apply_stagger,
    describe_stagger,
)


# ---------------------------------------------------------------------------
# StaggerConfig
# ---------------------------------------------------------------------------

def test_config_defaults():
    cfg = StaggerConfig()
    assert cfg.enabled is False
    assert cfg.interval_seconds == 0.0
    assert cfg.worker_index == 0
    assert cfg.total_workers == 1


def test_config_from_dict_full():
    cfg = StaggerConfig.from_dict(
        {"interval_seconds": 10.0, "worker_index": 2, "total_workers": 5}
    )
    assert cfg.enabled is True
    assert cfg.interval_seconds == 10.0
    assert cfg.worker_index == 2
    assert cfg.total_workers == 5


def test_config_from_dict_empty_uses_defaults():
    cfg = StaggerConfig.from_dict({})
    assert cfg.enabled is False
    assert cfg.interval_seconds == 0.0


def test_config_from_dict_invalid_type_raises():
    with pytest.raises(TypeError):
        StaggerConfig.from_dict("bad")


def test_config_negative_interval_raises():
    with pytest.raises(ValueError, match="interval_seconds"):
        StaggerConfig(enabled=True, interval_seconds=-1.0)


def test_config_zero_total_workers_raises():
    with pytest.raises(ValueError, match="total_workers"):
        StaggerConfig(enabled=True, interval_seconds=5.0, total_workers=0)


def test_config_index_gte_total_raises():
    with pytest.raises(ValueError, match="worker_index"):
        StaggerConfig(enabled=True, interval_seconds=5.0, worker_index=3, total_workers=3)


# ---------------------------------------------------------------------------
# compute_stagger_delay
# ---------------------------------------------------------------------------

def test_compute_delay_disabled_returns_zero():
    cfg = StaggerConfig(enabled=False, interval_seconds=10.0, worker_index=1, total_workers=4)
    assert compute_stagger_delay(cfg) == 0.0


def test_compute_delay_first_worker_is_zero():
    cfg = StaggerConfig(enabled=True, interval_seconds=10.0, worker_index=0, total_workers=4)
    assert compute_stagger_delay(cfg) == 0.0


def test_compute_delay_proportional():
    cfg = StaggerConfig(enabled=True, interval_seconds=8.0, worker_index=2, total_workers=4)
    assert compute_stagger_delay(cfg) == pytest.approx(4.0)


def test_compute_delay_last_worker():
    cfg = StaggerConfig(enabled=True, interval_seconds=10.0, worker_index=3, total_workers=4)
    assert compute_stagger_delay(cfg) == pytest.approx(7.5)


# ---------------------------------------------------------------------------
# apply_stagger (mocked sleep)
# ---------------------------------------------------------------------------

def test_apply_stagger_sleeps_correct_duration():
    cfg = StaggerConfig(enabled=True, interval_seconds=10.0, worker_index=1, total_workers=2)
    with patch("retryctl.stagger.time.sleep") as mock_sleep:
        slept = apply_stagger(cfg)
    mock_sleep.assert_called_once_with(pytest.approx(5.0))
    assert slept == pytest.approx(5.0)


def test_apply_stagger_disabled_no_sleep():
    cfg = StaggerConfig(enabled=False, interval_seconds=10.0)
    with patch("retryctl.stagger.time.sleep") as mock_sleep:
        slept = apply_stagger(cfg)
    mock_sleep.assert_not_called()
    assert slept == 0.0


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

def test_parse_stagger_empty_config():
    cfg = parse_stagger({})
    assert cfg.enabled is False


def test_parse_stagger_full_section():
    raw = {"stagger": {"interval_seconds": 6.0, "worker_index": 1, "total_workers": 3}}
    cfg = parse_stagger(raw)
    assert cfg.enabled is True
    assert cfg.interval_seconds == 6.0


def test_parse_stagger_invalid_section_raises():
    with pytest.raises(TypeError):
        parse_stagger({"stagger": "bad"})


def test_stagger_config_to_dict_roundtrip():
    cfg = StaggerConfig(enabled=True, interval_seconds=4.0, worker_index=1, total_workers=4)
    d = stagger_config_to_dict(cfg)
    assert d["enabled"] is True
    assert d["interval_seconds"] == 4.0
    assert d["worker_index"] == 1
    assert d["total_workers"] == 4


def test_maybe_apply_stagger_disabled_skips():
    cfg = StaggerConfig(enabled=False)
    with patch("retryctl.stagger_middleware.apply_stagger") as mock_apply:
        result = maybe_apply_stagger(cfg)
    mock_apply.assert_not_called()
    assert result == 0.0


def test_maybe_apply_stagger_enabled_delegates():
    cfg = StaggerConfig(enabled=True, interval_seconds=2.0, worker_index=1, total_workers=2)
    with patch("retryctl.stagger_middleware.apply_stagger", return_value=1.0) as mock_apply:
        result = maybe_apply_stagger(cfg)
    mock_apply.assert_called_once_with(cfg)
    assert result == 1.0


def test_describe_stagger_disabled():
    cfg = StaggerConfig()
    assert "disabled" in describe_stagger(cfg)


def test_describe_stagger_enabled():
    cfg = StaggerConfig(enabled=True, interval_seconds=10.0, worker_index=2, total_workers=5)
    desc = describe_stagger(cfg)
    assert "2/5" in desc
    assert "4.000" in desc
