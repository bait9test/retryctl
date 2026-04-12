"""Tests for retryctl.splay and retryctl.splay_middleware."""
from __future__ import annotations

import pytest

from retryctl.splay import (
    SplayConfig,
    apply_splay,
    compute_splay,
    from_dict,
)
from retryctl.splay_middleware import (
    describe_splay,
    maybe_apply_splay,
    parse_splay,
    splay_config_to_dict,
)


# ---------------------------------------------------------------------------
# SplayConfig / from_dict
# ---------------------------------------------------------------------------

def test_config_defaults():
    cfg = SplayConfig()
    assert cfg.enabled is False
    assert cfg.max_seconds == 0.0
    assert cfg.seed is None


def test_from_dict_full():
    cfg = from_dict({"enabled": True, "max_seconds": 5.0, "seed": 42})
    assert cfg.enabled is True
    assert cfg.max_seconds == 5.0
    assert cfg.seed == 42


def test_from_dict_empty_uses_defaults():
    cfg = from_dict({})
    assert cfg.enabled is False
    assert cfg.max_seconds == 0.0


def test_from_dict_auto_enables_when_max_set():
    cfg = from_dict({"max_seconds": 3.0})
    assert cfg.enabled is True


def test_from_dict_negative_max_raises():
    with pytest.raises(ValueError):
        from_dict({"max_seconds": -1.0})


def test_from_dict_invalid_type_raises():
    with pytest.raises(TypeError):
        from_dict("not a dict")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# compute_splay
# ---------------------------------------------------------------------------

def test_compute_splay_disabled_returns_zero():
    cfg = SplayConfig(enabled=False, max_seconds=10.0)
    assert compute_splay(cfg) == 0.0


def test_compute_splay_zero_max_returns_zero():
    cfg = SplayConfig(enabled=True, max_seconds=0.0)
    assert compute_splay(cfg) == 0.0


def test_compute_splay_within_range():
    cfg = SplayConfig(enabled=True, max_seconds=2.0, seed=7)
    delay = compute_splay(cfg)
    assert 0.0 <= delay <= 2.0


def test_compute_splay_deterministic_with_seed():
    cfg = SplayConfig(enabled=True, max_seconds=10.0, seed=99)
    d1 = compute_splay(cfg)
    d2 = compute_splay(cfg)
    assert d1 == d2


# ---------------------------------------------------------------------------
# apply_splay (mocked sleep)
# ---------------------------------------------------------------------------

def test_apply_splay_disabled_no_sleep(monkeypatch):
    slept = []
    monkeypatch.setattr("retryctl.splay.time.sleep", slept.append)
    cfg = SplayConfig(enabled=False, max_seconds=5.0)
    result = apply_splay(cfg)
    assert result == 0.0
    assert slept == []


def test_apply_splay_calls_sleep(monkeypatch):
    slept = []
    monkeypatch.setattr("retryctl.splay.time.sleep", slept.append)
    cfg = SplayConfig(enabled=True, max_seconds=3.0, seed=1)
    result = apply_splay(cfg)
    assert len(slept) == 1
    assert slept[0] == pytest.approx(result)


# ---------------------------------------------------------------------------
# Middleware helpers
# ---------------------------------------------------------------------------

def test_parse_splay_missing_section_uses_defaults():
    cfg = parse_splay({})
    assert cfg.enabled is False


def test_parse_splay_full_section():
    cfg = parse_splay({"splay": {"max_seconds": 4.0, "seed": 0}})
    assert cfg.enabled is True
    assert cfg.max_seconds == 4.0


def test_parse_splay_invalid_type_raises():
    with pytest.raises(TypeError):
        parse_splay({"splay": "bad"})


def test_splay_config_to_dict_roundtrip():
    cfg = SplayConfig(enabled=True, max_seconds=2.5, seed=3)
    d = splay_config_to_dict(cfg)
    assert d["enabled"] is True
    assert d["max_seconds"] == 2.5
    assert d["seed"] == 3


def test_describe_splay_disabled():
    cfg = SplayConfig(enabled=False)
    assert describe_splay(cfg) == "splay disabled"


def test_describe_splay_enabled():
    cfg = SplayConfig(enabled=True, max_seconds=6.0)
    assert "6.0" in describe_splay(cfg)


def test_maybe_apply_splay_disabled_no_sleep(monkeypatch):
    slept = []
    monkeypatch.setattr("retryctl.splay_middleware.time.sleep", slept.append)
    cfg = SplayConfig(enabled=False, max_seconds=5.0)
    result = maybe_apply_splay(cfg)
    assert result == 0.0
    assert slept == []


def test_maybe_apply_splay_enabled_sleeps(monkeypatch):
    slept = []
    monkeypatch.setattr("retryctl.splay_middleware.time.sleep", slept.append)
    cfg = SplayConfig(enabled=True, max_seconds=2.0, seed=5)
    result = maybe_apply_splay(cfg)
    assert len(slept) == 1
    assert 0.0 <= result <= 2.0
