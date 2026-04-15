"""Tests for retryctl.absorb and retryctl.absorb_middleware."""
from __future__ import annotations

import pytest

from retryctl.absorb import (
    AbsorbConfig,
    AbsorbState,
    check_absorbed,
    reset_absorb_state,
)
from retryctl.absorb_middleware import (
    absorb_config_to_dict,
    describe_absorb,
    on_attempt_failure,
    on_run_success,
    parse_absorb,
)


# ---------------------------------------------------------------------------
# AbsorbConfig
# ---------------------------------------------------------------------------

def test_config_defaults():
    cfg = AbsorbConfig()
    assert cfg.enabled is False
    assert cfg.threshold == 3


def test_from_dict_full():
    cfg = AbsorbConfig.from_dict({"enabled": True, "threshold": 5})
    assert cfg.enabled is True
    assert cfg.threshold == 5


def test_from_dict_auto_enables_when_threshold_set():
    cfg = AbsorbConfig.from_dict({"threshold": 2})
    assert cfg.enabled is True


def test_from_dict_empty_uses_defaults():
    cfg = AbsorbConfig.from_dict({})
    assert cfg.enabled is False
    assert cfg.threshold == 3


def test_from_dict_invalid_type_raises():
    with pytest.raises(TypeError):
        AbsorbConfig.from_dict("bad")


def test_from_dict_zero_threshold_raises():
    with pytest.raises(ValueError):
        AbsorbConfig.from_dict({"threshold": 0})


def test_from_dict_negative_threshold_raises():
    with pytest.raises(ValueError):
        AbsorbConfig.from_dict({"threshold": -1})


# ---------------------------------------------------------------------------
# AbsorbState
# ---------------------------------------------------------------------------

def test_state_initial():
    s = AbsorbState()
    assert s.consecutive_failures == 0


def test_state_record_failure_increments():
    s = AbsorbState()
    s.record_failure()
    s.record_failure()
    assert s.consecutive_failures == 2


def test_state_record_success_resets():
    s = AbsorbState()
    s.record_failure()
    s.record_success()
    assert s.consecutive_failures == 0


def test_is_absorbed_below_threshold():
    s = AbsorbState()
    s.record_failure()
    assert s.is_absorbed(threshold=3) is True


def test_is_absorbed_at_threshold():
    s = AbsorbState()
    for _ in range(3):
        s.record_failure()
    assert s.is_absorbed(threshold=3) is False


# ---------------------------------------------------------------------------
# check_absorbed / middleware helpers
# ---------------------------------------------------------------------------

def setup_function():
    # Clear shared state before each test function.
    reset_absorb_state("test_key")


def test_disabled_config_never_absorbs():
    cfg = AbsorbConfig(enabled=False, threshold=1)
    assert check_absorbed(cfg, "test_key", failed=True) is False


def test_absorbs_below_threshold():
    cfg = AbsorbConfig(enabled=True, threshold=3)
    assert on_attempt_failure(cfg, "test_key") is True  # 1st failure absorbed
    assert on_attempt_failure(cfg, "test_key") is True  # 2nd failure absorbed


def test_releases_at_threshold():
    cfg = AbsorbConfig(enabled=True, threshold=3)
    on_attempt_failure(cfg, "test_key")
    on_attempt_failure(cfg, "test_key")
    result = on_attempt_failure(cfg, "test_key")  # 3rd — at threshold
    assert result is False


def test_success_resets_counter():
    cfg = AbsorbConfig(enabled=True, threshold=2)
    on_attempt_failure(cfg, "test_key")
    on_run_success(cfg, "test_key")
    # After reset, single failure should be absorbed again.
    assert on_attempt_failure(cfg, "test_key") is True


# ---------------------------------------------------------------------------
# middleware helpers
# ---------------------------------------------------------------------------

def test_parse_absorb_missing_section_uses_defaults():
    cfg = parse_absorb({})
    assert cfg.enabled is False


def test_parse_absorb_full_section():
    cfg = parse_absorb({"absorb": {"enabled": True, "threshold": 4}})
    assert cfg.enabled is True
    assert cfg.threshold == 4


def test_parse_absorb_invalid_section_type_raises():
    with pytest.raises(TypeError):
        parse_absorb({"absorb": "bad"})


def test_absorb_config_to_dict_roundtrip():
    cfg = AbsorbConfig(enabled=True, threshold=7)
    d = absorb_config_to_dict(cfg)
    assert d == {"enabled": True, "threshold": 7}


def test_describe_absorb_disabled():
    assert "disabled" in describe_absorb(AbsorbConfig(enabled=False))


def test_describe_absorb_enabled():
    desc = describe_absorb(AbsorbConfig(enabled=True, threshold=5))
    assert "5" in desc
