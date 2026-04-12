"""Tests for retryctl.decay and retryctl.decay_middleware."""
from __future__ import annotations

import pytest

from retryctl.decay import DecayConfig, DecayTracker
from retryctl.decay_middleware import (
    apply_decay,
    decay_config_to_dict,
    describe_decay,
    on_attempt_failure,
    on_run_success,
    parse_decay,
)


# ---------------------------------------------------------------------------
# DecayConfig
# ---------------------------------------------------------------------------

def test_config_defaults():
    cfg = DecayConfig()
    assert cfg.enabled is False
    assert cfg.threshold == 3
    assert cfg.factor == 1.2
    assert cfg.max_multiplier == 8.0


def test_config_from_dict_full():
    cfg = DecayConfig.from_dict(
        {"enabled": True, "threshold": 5, "factor": 1.5, "max_multiplier": 4.0}
    )
    assert cfg.enabled is True
    assert cfg.threshold == 5
    assert cfg.factor == 1.5
    assert cfg.max_multiplier == 4.0


def test_config_from_dict_empty_uses_defaults():
    cfg = DecayConfig.from_dict({})
    assert cfg.enabled is False
    assert cfg.threshold == 3


def test_config_auto_enables_when_factor_supplied():
    cfg = DecayConfig.from_dict({"factor": 1.3})
    assert cfg.enabled is True


def test_config_invalid_type_raises():
    with pytest.raises(TypeError):
        DecayConfig.from_dict("not a dict")


def test_config_threshold_below_one_raises():
    with pytest.raises(ValueError):
        DecayConfig(threshold=0)


def test_config_factor_below_one_raises():
    with pytest.raises(ValueError):
        DecayConfig(factor=0.9)


def test_config_max_multiplier_below_one_raises():
    with pytest.raises(ValueError):
        DecayConfig(max_multiplier=0.5)


# ---------------------------------------------------------------------------
# DecayTracker
# ---------------------------------------------------------------------------

def _tracker(enabled=True, threshold=3, factor=2.0, max_multiplier=8.0):
    cfg = DecayConfig(enabled=enabled, threshold=threshold, factor=factor, max_multiplier=max_multiplier)
    return DecayTracker(config=cfg)


def test_multiplier_one_when_disabled():
    t = _tracker(enabled=False)
    for _ in range(10):
        t.record_failure()
    assert t.current_multiplier() == 1.0


def test_multiplier_one_below_threshold():
    t = _tracker(threshold=3)
    t.record_failure()
    t.record_failure()
    assert t.current_multiplier() == 1.0


def test_multiplier_grows_beyond_threshold():
    t = _tracker(threshold=2, factor=2.0)
    t.record_failure()
    t.record_failure()  # at threshold — still 1.0
    assert t.current_multiplier() == 1.0
    t.record_failure()  # 1 beyond threshold → 2^1 = 2.0
    assert t.current_multiplier() == 2.0
    t.record_failure()  # 2 beyond → 2^2 = 4.0
    assert t.current_multiplier() == 4.0


def test_multiplier_capped_at_max():
    t = _tracker(threshold=1, factor=2.0, max_multiplier=4.0)
    for _ in range(20):
        t.record_failure()
    assert t.current_multiplier() == 4.0


def test_success_resets_streak():
    t = _tracker(threshold=1, factor=2.0)
    t.record_failure()
    t.record_failure()
    assert t.current_multiplier() > 1.0
    t.record_success()
    assert t.current_multiplier() == 1.0


def test_apply_scales_delay():
    t = _tracker(threshold=1, factor=2.0)
    t.record_failure()
    t.record_failure()  # 1 beyond threshold → ×2
    assert t.apply(5.0) == pytest.approx(10.0)


# ---------------------------------------------------------------------------
# Middleware helpers
# ---------------------------------------------------------------------------

def test_parse_decay_empty_config():
    cfg = parse_decay({})
    assert cfg.enabled is False


def test_parse_decay_full_section():
    cfg = parse_decay({"decay": {"enabled": True, "threshold": 4, "factor": 1.5}})
    assert cfg.enabled is True
    assert cfg.threshold == 4


def test_parse_decay_invalid_section_type_raises():
    with pytest.raises(TypeError):
        parse_decay({"decay": "bad"})


def test_decay_config_to_dict_roundtrip():
    cfg = DecayConfig(enabled=True, threshold=5, factor=1.8, max_multiplier=6.0)
    d = decay_config_to_dict(cfg)
    assert d["enabled"] is True
    assert d["threshold"] == 5
    assert d["factor"] == 1.8
    assert d["max_multiplier"] == 6.0


def test_on_attempt_failure_increments():
    t = _tracker(threshold=1, factor=2.0)
    on_attempt_failure(t)
    on_attempt_failure(t)
    assert t.current_multiplier() == 2.0


def test_on_run_success_resets():
    t = _tracker(threshold=1, factor=2.0)
    on_attempt_failure(t)
    on_attempt_failure(t)
    on_run_success(t)
    assert t.current_multiplier() == 1.0


def test_apply_decay_helper():
    t = _tracker(threshold=1, factor=2.0)
    on_attempt_failure(t)
    on_attempt_failure(t)
    result = apply_decay(t, 3.0)
    assert result == pytest.approx(6.0)


def test_describe_decay_disabled():
    cfg = DecayConfig(enabled=False)
    assert "disabled" in describe_decay(cfg)


def test_describe_decay_enabled():
    cfg = DecayConfig(enabled=True, threshold=3, factor=1.2, max_multiplier=8.0)
    desc = describe_decay(cfg)
    assert "enabled" in desc
    assert "threshold=3" in desc
    assert "factor=1.2" in desc
