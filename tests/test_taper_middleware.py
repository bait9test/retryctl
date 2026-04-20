"""Tests for retryctl/taper_middleware.py."""
from __future__ import annotations

import pytest

from retryctl.taper import TaperConfig
from retryctl.taper_middleware import (
    describe_taper,
    make_state,
    on_attempt_failure,
    on_run_success,
    parse_taper,
    taper_config_to_dict,
)


# ---------------------------------------------------------------------------
# parse_taper
# ---------------------------------------------------------------------------

def test_parse_taper_empty_config_uses_defaults():
    cfg = parse_taper({})
    assert isinstance(cfg, TaperConfig)
    assert cfg.enabled is False


def test_parse_taper_missing_section_uses_defaults():
    cfg = parse_taper({"other": {"key": 1}})
    assert cfg.enabled is False


def test_parse_taper_full_section():
    raw = {"taper": {"enabled": True, "threshold": 3, "factor": 0.5, "min_multiplier": 0.1}}
    cfg = parse_taper(raw)
    assert cfg.enabled is True
    assert cfg.threshold == 3
    assert cfg.factor == pytest.approx(0.5)
    assert cfg.min_multiplier == pytest.approx(0.1)


def test_parse_taper_invalid_type_raises():
    with pytest.raises(TypeError, match="must be a table"):
        parse_taper({"taper": "bad"})


# ---------------------------------------------------------------------------
# taper_config_to_dict  (round-trip)
# ---------------------------------------------------------------------------

def test_taper_config_to_dict_roundtrip():
    raw = {"taper": {"enabled": True, "threshold": 5, "factor": 0.7, "min_multiplier": 0.2}}
    cfg = parse_taper(raw)
    d = taper_config_to_dict(cfg)
    assert d["enabled"] is True
    assert d["threshold"] == 5
    assert d["factor"] == pytest.approx(0.7)
    assert d["min_multiplier"] == pytest.approx(0.2)


# ---------------------------------------------------------------------------
# make_state / on_attempt_failure / on_run_success
# ---------------------------------------------------------------------------

def _enabled_cfg(threshold: int = 3, factor: float = 0.5, min_multiplier: float = 0.1) -> TaperConfig:
    return TaperConfig(enabled=True, threshold=threshold, factor=factor, min_multiplier=min_multiplier)


def test_make_state_returns_fresh_state():
    cfg = _enabled_cfg()
    state = make_state(cfg)
    assert state.consecutive_failures == 0
    assert not state.is_tapered()


def test_on_attempt_failure_below_threshold_not_tapered():
    cfg = _enabled_cfg(threshold=3)
    state = make_state(cfg)
    on_attempt_failure(state, attempt=1)
    on_attempt_failure(state, attempt=2)
    assert not state.is_tapered()


def test_on_attempt_failure_at_threshold_tapers():
    cfg = _enabled_cfg(threshold=3)
    state = make_state(cfg)
    for i in range(1, 4):
        on_attempt_failure(state, attempt=i)
    assert state.is_tapered()


def test_on_attempt_failure_returns_multiplier():
    cfg = _enabled_cfg(threshold=2, factor=0.5, min_multiplier=0.1)
    state = make_state(cfg)
    m1 = on_attempt_failure(state, attempt=1)
    m2 = on_attempt_failure(state, attempt=2)  # hits threshold
    assert m1 == pytest.approx(1.0)  # not yet tapered
    assert 0.0 < m2 < 1.0            # tapered


def test_on_run_success_resets_state():
    cfg = _enabled_cfg(threshold=2)
    state = make_state(cfg)
    on_attempt_failure(state, attempt=1)
    on_attempt_failure(state, attempt=2)
    assert state.is_tapered()
    on_run_success(state)
    assert not state.is_tapered()
    assert state.consecutive_failures == 0


# ---------------------------------------------------------------------------
# describe_taper
# ---------------------------------------------------------------------------

def test_describe_taper_disabled():
    cfg = TaperConfig(enabled=False)
    assert describe_taper(cfg) == "taper: disabled"


def test_describe_taper_enabled_contains_key_fields():
    cfg = _enabled_cfg(threshold=4, factor=0.6, min_multiplier=0.05)
    desc = describe_taper(cfg)
    assert "enabled" in desc
    assert "4" in desc
    assert "0.6" in desc
