"""Tests for retryctl/veil.py and retryctl/veil_middleware.py."""
from __future__ import annotations

import pytest

from retryctl.veil import (
    VeilConfig,
    VeilTracker,
    VeiledAttempt,
)
from retryctl.veil_middleware import (
    before_attempt,
    describe_veil,
    make_tracker,
    parse_veil,
    veil_config_to_dict,
)


# ---------------------------------------------------------------------------
# VeilConfig
# ---------------------------------------------------------------------------

def test_config_defaults():
    cfg = VeilConfig()
    assert cfg.enabled is False
    assert cfg.drop_rate == 0.0
    assert cfg.seed is None


def test_from_dict_full():
    cfg = VeilConfig.from_dict({"drop_rate": 0.3, "enabled": True, "seed": 42})
    assert cfg.enabled is True
    assert cfg.drop_rate == pytest.approx(0.3)
    assert cfg.seed == 42


def test_from_dict_auto_enables_when_rate_positive():
    cfg = VeilConfig.from_dict({"drop_rate": 0.1})
    assert cfg.enabled is True


def test_from_dict_empty_uses_defaults():
    cfg = VeilConfig.from_dict({})
    assert cfg.enabled is False
    assert cfg.drop_rate == 0.0


def test_from_dict_invalid_type_raises():
    with pytest.raises(TypeError):
        VeilConfig.from_dict("bad")


def test_from_dict_rate_out_of_range_raises():
    with pytest.raises(ValueError):
        VeilConfig.from_dict({"drop_rate": 1.5})


def test_from_dict_negative_rate_raises():
    with pytest.raises(ValueError):
        VeilConfig.from_dict({"drop_rate": -0.1})


# ---------------------------------------------------------------------------
# VeilTracker
# ---------------------------------------------------------------------------

def test_disabled_tracker_never_drops():
    cfg = VeilConfig(enabled=False, drop_rate=0.9)
    tracker = VeilTracker(config=cfg)
    for i in range(50):
        assert tracker.should_drop() is False


def test_zero_rate_never_drops():
    cfg = VeilConfig(enabled=True, drop_rate=0.0)
    tracker = VeilTracker(config=cfg)
    for i in range(50):
        assert tracker.should_drop() is False


def test_full_rate_always_drops():
    cfg = VeilConfig(enabled=True, drop_rate=1.0, seed=0)
    tracker = VeilTracker(config=cfg)
    for i in range(20):
        assert tracker.should_drop() is True


def test_seeded_rng_is_deterministic():
    cfg = VeilConfig(enabled=True, drop_rate=0.5, seed=7)
    t1 = VeilTracker(config=cfg)
    t2 = VeilTracker(config=cfg)
    results1 = [t1.should_drop() for _ in range(20)]
    results2 = [t2.should_drop() for _ in range(20)]
    assert results1 == results2


def test_check_raises_veiled_attempt():
    cfg = VeilConfig(enabled=True, drop_rate=1.0)
    tracker = VeilTracker(config=cfg)
    with pytest.raises(VeiledAttempt) as exc_info:
        tracker.check(3)
    assert exc_info.value.attempt == 3


def test_check_does_not_raise_when_not_dropped():
    cfg = VeilConfig(enabled=True, drop_rate=0.0)
    tracker = VeilTracker(config=cfg)
    tracker.check(1)  # should not raise


# ---------------------------------------------------------------------------
# Middleware helpers
# ---------------------------------------------------------------------------

def test_parse_veil_empty_config():
    cfg = parse_veil({})
    assert cfg.enabled is False


def test_parse_veil_full_section():
    cfg = parse_veil({"veil": {"drop_rate": 0.25, "seed": 99}})
    assert cfg.drop_rate == pytest.approx(0.25)
    assert cfg.seed == 99


def test_parse_veil_invalid_section_type_raises():
    with pytest.raises(TypeError):
        parse_veil({"veil": "oops"})


def test_veil_config_to_dict_roundtrip():
    cfg = VeilConfig(enabled=True, drop_rate=0.4, seed=1)
    d = veil_config_to_dict(cfg)
    assert d["enabled"] is True
    assert d["drop_rate"] == pytest.approx(0.4)
    assert d["seed"] == 1


def test_make_tracker_returns_tracker():
    cfg = VeilConfig(enabled=True, drop_rate=0.5, seed=0)
    tracker = make_tracker(cfg)
    assert isinstance(tracker, VeilTracker)


def test_before_attempt_raises_on_drop():
    cfg = VeilConfig(enabled=True, drop_rate=1.0)
    tracker = make_tracker(cfg)
    with pytest.raises(VeiledAttempt):
        before_attempt(tracker, 1)


def test_before_attempt_passes_when_no_drop():
    cfg = VeilConfig(enabled=True, drop_rate=0.0)
    tracker = make_tracker(cfg)
    before_attempt(tracker, 1)  # no exception


def test_describe_veil_disabled():
    assert describe_veil(VeilConfig()) == "veil disabled"


def test_describe_veil_enabled_no_seed():
    desc = describe_veil(VeilConfig(enabled=True, drop_rate=0.2))
    assert "20.00%" in desc
    assert "seed" not in desc


def test_describe_veil_enabled_with_seed():
    desc = describe_veil(VeilConfig(enabled=True, drop_rate=0.5, seed=42))
    assert "seed=42" in desc
