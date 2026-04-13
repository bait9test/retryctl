"""Tests for retryctl/clamp.py."""
import pytest

from retryctl.clamp import (
    ClampConfig,
    ClampViolation,
    describe_clamp,
    enforce_max,
    enforce_min,
)


# ---------------------------------------------------------------------------
# ClampConfig construction
# ---------------------------------------------------------------------------

def test_config_defaults():
    cfg = ClampConfig()
    assert cfg.enabled is False
    assert cfg.min_attempts == 1
    assert cfg.max_attempts == 0


def test_config_from_dict_full():
    cfg = ClampConfig.from_dict({"min_attempts": 2, "max_attempts": 10, "enabled": True})
    assert cfg.enabled is True
    assert cfg.min_attempts == 2
    assert cfg.max_attempts == 10


def test_config_from_dict_empty_uses_defaults():
    cfg = ClampConfig.from_dict({})
    assert cfg.min_attempts == 1
    assert cfg.max_attempts == 0
    assert cfg.enabled is False


def test_config_auto_enables_when_min_set():
    cfg = ClampConfig.from_dict({"min_attempts": 3})
    assert cfg.enabled is True


def test_config_auto_enables_when_max_set():
    cfg = ClampConfig.from_dict({"max_attempts": 5})
    assert cfg.enabled is True


def test_config_from_dict_invalid_type_raises():
    with pytest.raises(TypeError):
        ClampConfig.from_dict("bad")


def test_config_min_less_than_one_raises():
    with pytest.raises(ValueError, match="min_attempts"):
        ClampConfig(min_attempts=0)


def test_config_max_less_than_min_raises():
    with pytest.raises(ValueError, match="max_attempts"):
        ClampConfig(enabled=True, min_attempts=5, max_attempts=3)


def test_config_max_zero_is_unlimited():
    # max_attempts=0 means unlimited — should not raise
    cfg = ClampConfig(enabled=True, min_attempts=3, max_attempts=0)
    assert cfg.max_attempts == 0


# ---------------------------------------------------------------------------
# enforce_min
# ---------------------------------------------------------------------------

def test_enforce_min_disabled_always_passes():
    cfg = ClampConfig(enabled=False, min_attempts=5)
    enforce_min(cfg, attempts_so_far=1)  # no raise


def test_enforce_min_met_does_not_raise():
    cfg = ClampConfig(enabled=True, min_attempts=2)
    enforce_min(cfg, attempts_so_far=2)
    enforce_min(cfg, attempts_so_far=10)


def test_enforce_min_not_met_raises():
    cfg = ClampConfig(enabled=True, min_attempts=3)
    with pytest.raises(ClampViolation, match="minimum 3"):
        enforce_min(cfg, attempts_so_far=2)


# ---------------------------------------------------------------------------
# enforce_max
# ---------------------------------------------------------------------------

def test_enforce_max_disabled_always_passes():
    cfg = ClampConfig(enabled=False, max_attempts=2)
    enforce_max(cfg, next_attempt=100)  # no raise


def test_enforce_max_zero_means_unlimited():
    cfg = ClampConfig(enabled=True, min_attempts=1, max_attempts=0)
    enforce_max(cfg, next_attempt=999)  # no raise


def test_enforce_max_within_bound_does_not_raise():
    cfg = ClampConfig(enabled=True, min_attempts=1, max_attempts=5)
    enforce_max(cfg, next_attempt=5)


def test_enforce_max_exceeded_raises():
    cfg = ClampConfig(enabled=True, min_attempts=1, max_attempts=5)
    with pytest.raises(ClampViolation, match="max_attempts=5"):
        enforce_max(cfg, next_attempt=6)


# ---------------------------------------------------------------------------
# describe_clamp
# ---------------------------------------------------------------------------

def test_describe_clamp_disabled():
    assert describe_clamp(ClampConfig()) == "clamp disabled"


def test_describe_clamp_with_bounds():
    cfg = ClampConfig(enabled=True, min_attempts=2, max_attempts=8)
    desc = describe_clamp(cfg)
    assert "min=2" in desc
    assert "max=8" in desc


def test_describe_clamp_unlimited_max():
    cfg = ClampConfig(enabled=True, min_attempts=1, max_attempts=0)
    assert "unlimited" in describe_clamp(cfg)
