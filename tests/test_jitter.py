"""Tests for retryctl.jitter."""
import pytest

from retryctl.jitter import JitterConfig, JitterStrategy, apply_jitter


# ---------------------------------------------------------------------------
# JitterConfig.from_dict
# ---------------------------------------------------------------------------

def test_from_dict_defaults():
    cfg = JitterConfig.from_dict({})
    assert cfg.strategy == JitterStrategy.NONE
    assert cfg.max_ms is None
    assert cfg.seed is None


def test_from_dict_full():
    cfg = JitterConfig.from_dict({"strategy": "full", "max_ms": 500, "seed": 42})
    assert cfg.strategy == JitterStrategy.FULL
    assert cfg.max_ms == 500
    assert cfg.seed == 42


def test_from_dict_invalid_strategy_raises():
    with pytest.raises(ValueError, match="Unknown jitter strategy"):
        JitterConfig.from_dict({"strategy": "banana"})


def test_from_dict_negative_max_ms_raises():
    with pytest.raises(ValueError, match="max_ms must be >= 0"):
        JitterConfig.from_dict({"strategy": "full", "max_ms": -1})


def test_from_dict_zero_max_ms_allowed():
    cfg = JitterConfig.from_dict({"max_ms": 0})
    assert cfg.max_ms == 0


# ---------------------------------------------------------------------------
# apply_jitter — NONE strategy
# ---------------------------------------------------------------------------

def test_none_strategy_returns_base():
    cfg = JitterConfig(strategy=JitterStrategy.NONE)
    assert apply_jitter(2.5, cfg) == 2.5


def test_none_strategy_zero_delay():
    cfg = JitterConfig(strategy=JitterStrategy.NONE)
    assert apply_jitter(0.0, cfg) == 0.0


# ---------------------------------------------------------------------------
# apply_jitter — FULL strategy
# ---------------------------------------------------------------------------

def test_full_strategy_within_range():
    cfg = JitterConfig(strategy=JitterStrategy.FULL, seed=7)
    result = apply_jitter(4.0, cfg)
    assert 0.0 <= result <= 4.0


def test_full_strategy_never_negative():
    cfg = JitterConfig(strategy=JitterStrategy.FULL, seed=99)
    assert apply_jitter(0.0, cfg) >= 0.0


# ---------------------------------------------------------------------------
# apply_jitter — EQUAL strategy
# ---------------------------------------------------------------------------

def test_equal_strategy_within_range():
    cfg = JitterConfig(strategy=JitterStrategy.EQUAL, seed=3)
    result = apply_jitter(6.0, cfg)
    assert 3.0 <= result <= 6.0


# ---------------------------------------------------------------------------
# apply_jitter — DECORRELATED strategy
# ---------------------------------------------------------------------------

def test_decorrelated_strategy_at_least_base():
    cfg = JitterConfig(strategy=JitterStrategy.DECORRELATED, seed=1)
    result = apply_jitter(1.0, cfg, prev_delay=1.0)
    assert result >= 1.0


def test_decorrelated_strategy_first_call_no_prev():
    cfg = JitterConfig(strategy=JitterStrategy.DECORRELATED, seed=5)
    # prev_delay=0 => upper = max(base, 0) = base => result == base
    result = apply_jitter(2.0, cfg, prev_delay=0.0)
    assert result == pytest.approx(2.0)


# ---------------------------------------------------------------------------
# max_ms cap
# ---------------------------------------------------------------------------

def test_max_ms_caps_added_jitter():
    # With FULL strategy the result can be at most base + max_ms/1000
    cfg = JitterConfig(strategy=JitterStrategy.FULL, max_ms=100, seed=0)
    base = 10.0
    result = apply_jitter(base, cfg)
    # full jitter samples in [0, base]; cap = base + 0.1
    assert result <= base + 0.1 + 1e-9


def test_max_ms_zero_clamps_to_base_for_none():
    cfg = JitterConfig(strategy=JitterStrategy.NONE, max_ms=0)
    assert apply_jitter(3.0, cfg) == pytest.approx(3.0)
