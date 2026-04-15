"""Tests for retryctl.shimmer and retryctl.shimmer_middleware."""
from __future__ import annotations

import pytest

from retryctl.shimmer import (
    ShimmerConfig,
    ShimmerSkipped,
    ShimmerTracker,
)
from retryctl.shimmer_middleware import (
    before_attempt,
    describe_shimmer,
    make_tracker,
    parse_shimmer,
    shimmer_config_to_dict,
)


# ---------------------------------------------------------------------------
# ShimmerConfig
# ---------------------------------------------------------------------------

def test_config_defaults():
    cfg = ShimmerConfig()
    assert cfg.enabled is False
    assert cfg.skip_rate == 0.0
    assert cfg.seed is None


def test_from_dict_full():
    cfg = ShimmerConfig.from_dict({"skip_rate": 0.5, "enabled": True, "seed": 42})
    assert cfg.enabled is True
    assert cfg.skip_rate == 0.5
    assert cfg.seed == 42


def test_from_dict_auto_enables_when_skip_rate_positive():
    cfg = ShimmerConfig.from_dict({"skip_rate": 0.3})
    assert cfg.enabled is True


def test_from_dict_empty_uses_defaults():
    cfg = ShimmerConfig.from_dict({})
    assert cfg.enabled is False
    assert cfg.skip_rate == 0.0


def test_from_dict_invalid_type_raises():
    with pytest.raises(TypeError):
        ShimmerConfig.from_dict("bad")


def test_config_invalid_skip_rate_raises():
    with pytest.raises(ValueError):
        ShimmerConfig(enabled=True, skip_rate=1.5)


def test_config_negative_skip_rate_raises():
    with pytest.raises(ValueError):
        ShimmerConfig(enabled=True, skip_rate=-0.1)


# ---------------------------------------------------------------------------
# ShimmerTracker
# ---------------------------------------------------------------------------

def test_disabled_tracker_never_skips():
    cfg = ShimmerConfig(enabled=False, skip_rate=0.9, seed=0)
    tracker = ShimmerTracker(cfg)
    for i in range(20):
        assert tracker.should_skip(i) is False
    assert tracker.skipped == 0
    assert tracker.allowed == 20


def test_zero_rate_never_skips():
    cfg = ShimmerConfig(enabled=True, skip_rate=0.0, seed=0)
    tracker = ShimmerTracker(cfg)
    for i in range(10):
        assert tracker.should_skip(i) is False


def test_full_rate_always_skips():
    cfg = ShimmerConfig(enabled=True, skip_rate=1.0, seed=7)
    tracker = ShimmerTracker(cfg)
    for i in range(10):
        assert tracker.should_skip(i) is True
    assert tracker.allowed == 0
    assert tracker.skipped == 10


def test_check_raises_shimmer_skipped():
    cfg = ShimmerConfig(enabled=True, skip_rate=1.0)
    tracker = ShimmerTracker(cfg)
    with pytest.raises(ShimmerSkipped) as exc_info:
        tracker.check(3)
    assert exc_info.value.attempt == 3


def test_seeded_rng_is_deterministic():
    cfg = ShimmerConfig(enabled=True, skip_rate=0.5, seed=99)
    t1 = ShimmerTracker(cfg)
    t2 = ShimmerTracker(cfg)
    results1 = [t1.should_skip(i) for i in range(20)]
    results2 = [t2.should_skip(i) for i in range(20)]
    assert results1 == results2


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

def test_parse_shimmer_missing_section_uses_defaults():
    cfg = parse_shimmer({})
    assert cfg.enabled is False


def test_parse_shimmer_full_section():
    cfg = parse_shimmer({"shimmer": {"skip_rate": 0.25, "seed": 1}})
    assert cfg.skip_rate == 0.25
    assert cfg.seed == 1


def test_parse_shimmer_invalid_type_raises():
    with pytest.raises(TypeError):
        parse_shimmer({"shimmer": "bad"})


def test_shimmer_config_to_dict_roundtrip():
    cfg = ShimmerConfig(enabled=True, skip_rate=0.4, seed=5)
    d = shimmer_config_to_dict(cfg)
    assert d["enabled"] is True
    assert d["skip_rate"] == 0.4
    assert d["seed"] == 5


def test_before_attempt_raises_when_skipped():
    cfg = ShimmerConfig(enabled=True, skip_rate=1.0)
    tracker = make_tracker(cfg)
    with pytest.raises(ShimmerSkipped):
        before_attempt(tracker, 1)


def test_before_attempt_passes_when_not_skipped():
    cfg = ShimmerConfig(enabled=False)
    tracker = make_tracker(cfg)
    before_attempt(tracker, 1)  # should not raise


def test_describe_shimmer_disabled():
    assert "disabled" in describe_shimmer(ShimmerConfig())


def test_describe_shimmer_enabled():
    desc = describe_shimmer(ShimmerConfig(enabled=True, skip_rate=0.2))
    assert "20%" in desc


def test_describe_shimmer_with_seed():
    desc = describe_shimmer(ShimmerConfig(enabled=True, skip_rate=0.1, seed=42))
    assert "seed=42" in desc
