"""Tests for retryctl.mute and retryctl.mute_middleware."""
from __future__ import annotations

import pytest

from retryctl.mute import MuteConfig, is_muted, mute_config_summary
from retryctl.mute_middleware import (
    check_mute,
    describe_mute,
    mute_config_to_dict,
    parse_mute,
)


# ---------------------------------------------------------------------------
# MuteConfig.from_dict
# ---------------------------------------------------------------------------

def test_config_defaults():
    cfg = MuteConfig()
    assert cfg.enabled is False
    assert cfg.exit_codes == []
    assert cfg.patterns == []
    assert cfg.suppress_alerts is True
    assert cfg.suppress_output is False


def test_from_dict_auto_enables_when_exit_codes_set():
    cfg = MuteConfig.from_dict({"exit_codes": [0, 1]})
    assert cfg.enabled is True
    assert cfg.exit_codes == [0, 1]


def test_from_dict_auto_enables_when_patterns_set():
    cfg = MuteConfig.from_dict({"patterns": ["WARN"]})
    assert cfg.enabled is True
    assert cfg.patterns == ["WARN"]


def test_from_dict_explicit_disabled_overrides():
    cfg = MuteConfig.from_dict({"exit_codes": [1], "enabled": False})
    assert cfg.enabled is False


def test_from_dict_invalid_type_raises():
    with pytest.raises(TypeError):
        MuteConfig.from_dict("bad")


def test_from_dict_exit_codes_not_list_raises():
    with pytest.raises(TypeError):
        MuteConfig.from_dict({"exit_codes": 1})


def test_from_dict_patterns_not_list_raises():
    with pytest.raises(TypeError):
        MuteConfig.from_dict({"patterns": "WARN"})


def test_from_dict_suppress_flags():
    cfg = MuteConfig.from_dict(
        {"exit_codes": [0], "suppress_alerts": False, "suppress_output": True}
    )
    assert cfg.suppress_alerts is False
    assert cfg.suppress_output is True


# ---------------------------------------------------------------------------
# is_muted
# ---------------------------------------------------------------------------

def test_disabled_config_never_mutes():
    cfg = MuteConfig(enabled=False, exit_codes=[0])
    assert is_muted(cfg, 0) is False


def test_muted_by_exit_code():
    cfg = MuteConfig.from_dict({"exit_codes": [2]})
    assert is_muted(cfg, 2) is True
    assert is_muted(cfg, 1) is False


def test_muted_by_pattern():
    cfg = MuteConfig.from_dict({"patterns": [r"transient error"]})
    assert is_muted(cfg, 1, output="transient error occurred") is True
    assert is_muted(cfg, 1, output="fatal crash") is False


def test_exit_code_takes_priority_over_pattern():
    cfg = MuteConfig.from_dict({"exit_codes": [3], "patterns": ["ok"]})
    # exit code match — no need to check pattern
    assert is_muted(cfg, 3, output="unrelated") is True


# ---------------------------------------------------------------------------
# mute_config_summary
# ---------------------------------------------------------------------------

def test_summary_disabled_returns_none():
    assert mute_config_summary(MuteConfig()) is None


def test_summary_includes_exit_codes():
    cfg = MuteConfig.from_dict({"exit_codes": [1, 2]})
    s = mute_config_summary(cfg)
    assert s is not None
    assert "exit_codes" in s


# ---------------------------------------------------------------------------
# middleware helpers
# ---------------------------------------------------------------------------

def test_parse_mute_missing_section_uses_defaults():
    cfg = parse_mute({})
    assert cfg.enabled is False


def test_parse_mute_full_section():
    cfg = parse_mute({"mute": {"exit_codes": [0], "suppress_output": True}})
    assert cfg.enabled is True
    assert 0 in cfg.exit_codes
    assert cfg.suppress_output is True


def test_mute_config_to_dict_roundtrip():
    original = MuteConfig.from_dict({"exit_codes": [1], "patterns": ["ERR"]})
    d = mute_config_to_dict(original)
    restored = MuteConfig.from_dict(d)
    assert restored.exit_codes == original.exit_codes
    assert restored.patterns == original.patterns


def test_check_mute_disabled_returns_false():
    cfg = MuteConfig()
    assert check_mute(cfg, 1, output="anything") is False


def test_check_mute_returns_true_on_match():
    cfg = MuteConfig.from_dict({"exit_codes": [42]})
    assert check_mute(cfg, 42) is True


def test_describe_mute_disabled():
    assert describe_mute(MuteConfig()) == "mute(disabled)"


def test_describe_mute_enabled():
    cfg = MuteConfig.from_dict({"exit_codes": [0]})
    desc = describe_mute(cfg)
    assert desc.startswith("mute(")
