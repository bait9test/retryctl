"""Tests for retryctl.slop and retryctl.slop_middleware."""
from __future__ import annotations

import pytest

from retryctl.slop import SlopConfig, SlopTracker, SlopAbsorbed
from retryctl.slop_middleware import (
    parse_slop,
    slop_config_to_dict,
    make_tracker,
    on_attempt_marginal,
    on_run_success,
    describe_slop,
)


# ---------------------------------------------------------------------------
# SlopConfig
# ---------------------------------------------------------------------------

def test_config_defaults():
    cfg = SlopConfig()
    assert cfg.enabled is False
    assert cfg.tolerance_codes == []
    assert cfg.window == 3


def test_from_dict_full():
    cfg = SlopConfig.from_dict({"tolerance_codes": [1, 2], "window": 5, "enabled": True})
    assert cfg.enabled is True
    assert cfg.tolerance_codes == [1, 2]
    assert cfg.window == 5


def test_from_dict_empty_uses_defaults():
    cfg = SlopConfig.from_dict({})
    assert cfg.enabled is False
    assert cfg.window == 3


def test_from_dict_auto_enables_when_codes_set():
    cfg = SlopConfig.from_dict({"tolerance_codes": [42]})
    assert cfg.enabled is True


def test_from_dict_invalid_type_raises():
    with pytest.raises(TypeError):
        SlopConfig.from_dict("bad")


def test_from_dict_zero_window_raises():
    with pytest.raises(ValueError):
        SlopConfig.from_dict({"window": 0, "tolerance_codes": [1]})


def test_from_dict_negative_window_raises():
    with pytest.raises(ValueError):
        SlopConfig.from_dict({"window": -1})


# ---------------------------------------------------------------------------
# SlopTracker
# ---------------------------------------------------------------------------

def _make_tracker(codes=(1, 2), window=3) -> SlopTracker:
    cfg = SlopConfig(enabled=True, tolerance_codes=list(codes), window=window)
    return SlopTracker(cfg)


def test_is_marginal_true():
    t = _make_tracker(codes=[1, 2])
    assert t.is_marginal(1) is True
    assert t.is_marginal(2) is True


def test_is_marginal_false():
    t = _make_tracker(codes=[1])
    assert t.is_marginal(99) is False


def test_absorbs_within_window():
    t = _make_tracker(window=2)
    with pytest.raises(SlopAbsorbed) as exc_info:
        t.check(1)
    assert exc_info.value.remaining == 1


def test_exhausted_after_window():
    t = _make_tracker(window=2)
    t.check(1)  # absorbed, remaining=1 — wait, raises
    # consume both slots
    try:
        t.check(1)
    except SlopAbsorbed:
        pass
    try:
        t.check(1)
    except SlopAbsorbed:
        pass
    # now exhausted — no exception raised
    assert t.exhausted() is True
    t.check(1)  # should NOT raise


def test_reset_clears_count():
    t = _make_tracker(window=1)
    try:
        t.check(1)
    except SlopAbsorbed:
        pass
    t.reset()
    assert not t.exhausted()


def test_disabled_tracker_never_absorbs():
    cfg = SlopConfig(enabled=False, tolerance_codes=[1], window=10)
    t = SlopTracker(cfg)
    t.check(1)  # should not raise


# ---------------------------------------------------------------------------
# Middleware helpers
# ---------------------------------------------------------------------------

def test_parse_slop_empty_config():
    cfg = parse_slop({})
    assert cfg.enabled is False


def test_parse_slop_full_section():
    cfg = parse_slop({"slop": {"tolerance_codes": [3], "window": 4}})
    assert cfg.tolerance_codes == [3]
    assert cfg.window == 4


def test_parse_slop_invalid_type_raises():
    with pytest.raises(TypeError):
        parse_slop({"slop": "bad"})


def test_slop_config_to_dict_roundtrip():
    cfg = SlopConfig(enabled=True, tolerance_codes=[5, 6], window=2)
    d = slop_config_to_dict(cfg)
    cfg2 = SlopConfig.from_dict(d)
    assert cfg2.tolerance_codes == [5, 6]
    assert cfg2.window == 2


def test_on_attempt_marginal_returns_true_when_absorbed():
    t = _make_tracker(codes=[1], window=3)
    result = on_attempt_marginal(t, 1)
    assert result is True


def test_on_attempt_marginal_returns_false_for_non_marginal():
    t = _make_tracker(codes=[1], window=3)
    result = on_attempt_marginal(t, 99)
    assert result is False


def test_on_run_success_resets_tracker():
    t = _make_tracker(window=1)
    on_attempt_marginal(t, 1)  # absorb one
    on_run_success(t)
    assert not t.exhausted()


def test_describe_slop_disabled():
    cfg = SlopConfig()
    assert "disabled" in describe_slop(cfg)


def test_describe_slop_enabled():
    cfg = SlopConfig(enabled=True, tolerance_codes=[1, 2], window=4)
    desc = describe_slop(cfg)
    assert "window=4" in desc
    assert "[1, 2]" in desc
