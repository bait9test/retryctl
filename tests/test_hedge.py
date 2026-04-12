"""Tests for retryctl.hedge and retryctl.hedge_middleware."""
from __future__ import annotations

import sys
import time

import pytest

from retryctl.hedge import (
    HedgeConfig,
    HedgeResult,
    from_dict,
    run_hedged,
)
from retryctl.hedge_middleware import (
    describe_hedge,
    hedge_config_to_dict,
    maybe_run_hedged,
    parse_hedge,
)


# ---------------------------------------------------------------------------
# HedgeConfig / from_dict
# ---------------------------------------------------------------------------

def test_config_defaults():
    cfg = HedgeConfig()
    assert cfg.enabled is False
    assert cfg.delay_ms == 500
    assert cfg.max_hedges == 1


def test_config_negative_delay_raises():
    with pytest.raises(ValueError, match="delay_ms"):
        HedgeConfig(delay_ms=-1)


def test_config_zero_max_hedges_raises():
    with pytest.raises(ValueError, match="max_hedges"):
        HedgeConfig(max_hedges=0)


def test_from_dict_full():
    cfg = from_dict({"enabled": True, "delay_ms": 200, "max_hedges": 2})
    assert cfg.enabled is True
    assert cfg.delay_ms == 200
    assert cfg.max_hedges == 2


def test_from_dict_empty_uses_defaults():
    cfg = from_dict({})
    assert cfg.delay_ms == 500
    assert cfg.max_hedges == 1


def test_from_dict_invalid_type_raises():
    with pytest.raises(TypeError):
        from_dict("not-a-dict")


# ---------------------------------------------------------------------------
# run_hedged — functional tests using real subprocesses
# ---------------------------------------------------------------------------

def _py(snippet: str):
    return [sys.executable, "-c", snippet]


def test_run_hedged_fast_original_wins():
    cmd = _py("import sys; sys.exit(0)")
    cfg = HedgeConfig(enabled=True, delay_ms=200, max_hedges=1)
    result = run_hedged(cmd, cfg)
    assert result.returncode == 0
    assert result.winner_index == 0


def test_run_hedged_returns_hedge_result_type():
    cmd = _py("print('hello')")
    cfg = HedgeConfig(enabled=True, delay_ms=50, max_hedges=1)
    result = run_hedged(cmd, cfg)
    assert isinstance(result, HedgeResult)
    assert b"hello" in result.stdout


def test_run_hedged_nonzero_returncode_propagated():
    cmd = _py("import sys; sys.exit(3)")
    cfg = HedgeConfig(enabled=True, delay_ms=50, max_hedges=1)
    result = run_hedged(cmd, cfg)
    assert result.returncode == 3


# ---------------------------------------------------------------------------
# hedge_middleware helpers
# ---------------------------------------------------------------------------

def test_parse_hedge_empty_config():
    cfg = parse_hedge({})
    assert cfg.enabled is False


def test_parse_hedge_full_section():
    cfg = parse_hedge({"hedge": {"enabled": True, "delay_ms": 100}})
    assert cfg.enabled is True
    assert cfg.delay_ms == 100


def test_parse_hedge_invalid_section_type_raises():
    with pytest.raises(TypeError):
        parse_hedge({"hedge": "bad"})


def test_hedge_config_to_dict_roundtrip():
    cfg = HedgeConfig(enabled=True, delay_ms=300, max_hedges=2)
    d = hedge_config_to_dict(cfg)
    assert d == {"enabled": True, "delay_ms": 300, "max_hedges": 2}


def test_maybe_run_hedged_disabled_runs_directly():
    cmd = _py("print('direct')")
    cfg = HedgeConfig(enabled=False)
    result = maybe_run_hedged(cmd, cfg)
    assert isinstance(result, HedgeResult)
    assert b"direct" in result.stdout
    assert result.winner_index == 0


def test_maybe_run_hedged_enabled_returns_result():
    cmd = _py("import sys; sys.exit(0)")
    cfg = HedgeConfig(enabled=True, delay_ms=50, max_hedges=1)
    result = maybe_run_hedged(cmd, cfg)
    assert result.returncode == 0


def test_describe_hedge_disabled():
    assert "disabled" in describe_hedge(HedgeConfig(enabled=False))


def test_describe_hedge_enabled():
    cfg = HedgeConfig(enabled=True, delay_ms=250, max_hedges=2)
    desc = describe_hedge(cfg)
    assert "250" in desc
    assert "max_hedges=2" in desc
