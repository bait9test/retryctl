"""Tests for retryctl.cloak and retryctl.cloak_middleware."""
from __future__ import annotations

import pytest

from retryctl.cloak import CloakConfig, CloakTracker, CloakedAttempt
from retryctl.cloak_middleware import (
    parse_cloak,
    cloak_config_to_dict,
    make_tracker,
    before_attempt,
    describe_cloak,
)


# ---------------------------------------------------------------------------
# CloakConfig
# ---------------------------------------------------------------------------

def test_config_defaults():
    cfg = CloakConfig()
    assert cfg.enabled is False
    assert cfg.mask_rate == 0.0
    assert cfg.seed is None
    assert cfg.tag == "cloaked"


def test_from_dict_full():
    cfg = CloakConfig.from_dict({"mask_rate": 0.5, "seed": 42, "tag": "hidden"})
    assert cfg.enabled is True
    assert cfg.mask_rate == 0.5
    assert cfg.seed == 42
    assert cfg.tag == "hidden"


def test_from_dict_empty_uses_defaults():
    cfg = CloakConfig.from_dict({})
    assert cfg.enabled is False
    assert cfg.mask_rate == 0.0


def test_from_dict_invalid_type_raises():
    with pytest.raises(TypeError):
        CloakConfig.from_dict("bad")


def test_from_dict_negative_mask_rate_raises():
    with pytest.raises(ValueError):
        CloakConfig.from_dict({"mask_rate": -0.1})


def test_from_dict_mask_rate_above_one_raises():
    with pytest.raises(ValueError):
        CloakConfig.from_dict({"mask_rate": 1.1})


def test_from_dict_explicit_disabled_overrides():
    cfg = CloakConfig.from_dict({"enabled": False, "mask_rate": 0.9})
    assert cfg.enabled is False


# ---------------------------------------------------------------------------
# CloakTracker
# ---------------------------------------------------------------------------

def test_disabled_tracker_never_cloaks():
    tracker = CloakTracker(CloakConfig(enabled=False, mask_rate=1.0))
    for i in range(10):
        assert tracker.is_cloaked(i) is False
    assert tracker.cloaked_attempts == []


def test_full_rate_always_cloaks():
    cfg = CloakConfig(enabled=True, mask_rate=1.0, seed=0)
    tracker = CloakTracker(cfg)
    for i in range(5):
        assert tracker.is_cloaked(i) is True
    assert tracker.cloaked_attempts == [0, 1, 2, 3, 4]


def test_zero_rate_never_cloaks():
    cfg = CloakConfig(enabled=True, mask_rate=0.0, seed=0)
    tracker = CloakTracker(cfg)
    for i in range(10):
        assert tracker.is_cloaked(i) is False


def test_seeded_results_are_reproducible():
    cfg = CloakConfig(enabled=True, mask_rate=0.5, seed=7)
    t1 = CloakTracker(cfg)
    t2 = CloakTracker(cfg)
    results1 = [t1.is_cloaked(i) for i in range(20)]
    results2 = [t2.is_cloaked(i) for i in range(20)]
    assert results1 == results2


def test_summary_reflects_count():
    cfg = CloakConfig(enabled=True, mask_rate=1.0, seed=0, tag="ghost")
    tracker = CloakTracker(cfg)
    for i in range(3):
        tracker.is_cloaked(i)
    assert "3" in tracker.summary()
    assert "ghost" in tracker.summary()


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

def test_parse_cloak_empty_config():
    cfg = parse_cloak({})
    assert cfg.enabled is False


def test_parse_cloak_full_section():
    cfg = parse_cloak({"cloak": {"mask_rate": 0.3, "seed": 1}})
    assert cfg.mask_rate == pytest.approx(0.3)


def test_parse_cloak_invalid_type_raises():
    with pytest.raises(TypeError):
        parse_cloak({"cloak": "bad"})


def test_cloak_config_to_dict_roundtrip():
    cfg = CloakConfig(enabled=True, mask_rate=0.25, seed=99, tag="shadow")
    d = cloak_config_to_dict(cfg)
    cfg2 = CloakConfig.from_dict(d)
    assert cfg2.mask_rate == cfg.mask_rate
    assert cfg2.seed == cfg.seed
    assert cfg2.tag == cfg.tag


def test_before_attempt_raises_when_cloaked():
    cfg = CloakConfig(enabled=True, mask_rate=1.0, seed=0)
    tracker = make_tracker(cfg)
    with pytest.raises(CloakedAttempt) as exc_info:
        before_attempt(tracker, 1)
    assert exc_info.value.attempt == 1


def test_before_attempt_silent_when_not_cloaked():
    cfg = CloakConfig(enabled=True, mask_rate=0.0, seed=0)
    tracker = make_tracker(cfg)
    before_attempt(tracker, 1)  # should not raise


def test_describe_cloak_disabled():
    assert "disabled" in describe_cloak(CloakConfig())


def test_describe_cloak_enabled():
    cfg = CloakConfig(enabled=True, mask_rate=0.4, tag="hidden")
    desc = describe_cloak(cfg)
    assert "40%" in desc
    assert "hidden" in desc


def test_describe_cloak_shows_seed_when_set():
    cfg = CloakConfig(enabled=True, mask_rate=0.1, seed=5)
    assert "seed=5" in describe_cloak(cfg)
