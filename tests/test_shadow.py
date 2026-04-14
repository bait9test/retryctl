"""Tests for retryctl.shadow and retryctl.shadow_middleware."""
from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest

from retryctl.shadow import (
    ShadowConfig,
    ShadowResult,
    compare_shadow,
    run_shadow,
)
from retryctl.shadow_middleware import (
    describe_shadow,
    maybe_run_shadow,
    parse_shadow,
    shadow_config_to_dict,
)


# ---------------------------------------------------------------------------
# ShadowConfig.from_dict
# ---------------------------------------------------------------------------

def test_config_defaults():
    cfg = ShadowConfig()
    assert cfg.enabled is False
    assert cfg.command == []
    assert cfg.timeout == 10.0
    assert cfg.log_divergence is True


def test_from_dict_full():
    cfg = ShadowConfig.from_dict(
        {"command": ["echo", "hi"], "timeout": 5.0, "log_divergence": False, "enabled": True}
    )
    assert cfg.enabled is True
    assert cfg.command == ["echo", "hi"]
    assert cfg.timeout == 5.0
    assert cfg.log_divergence is False


def test_from_dict_string_command_splits():
    cfg = ShadowConfig.from_dict({"command": "echo hello world"})
    assert cfg.command == ["echo", "hello", "world"]
    assert cfg.enabled is True  # auto-enabled when command present


def test_from_dict_empty_uses_defaults():
    cfg = ShadowConfig.from_dict({})
    assert cfg.enabled is False
    assert cfg.command == []


def test_from_dict_invalid_type_raises():
    with pytest.raises(TypeError):
        ShadowConfig.from_dict("not-a-dict")


def test_from_dict_invalid_command_type_raises():
    with pytest.raises(TypeError):
        ShadowConfig.from_dict({"command": 123})


def test_from_dict_zero_timeout_raises():
    with pytest.raises(ValueError):
        ShadowConfig.from_dict({"command": ["echo"], "timeout": 0})


def test_from_dict_negative_timeout_raises():
    with pytest.raises(ValueError):
        ShadowConfig.from_dict({"command": ["echo"], "timeout": -1})


# ---------------------------------------------------------------------------
# run_shadow
# ---------------------------------------------------------------------------

def test_run_shadow_disabled_returns_none():
    cfg = ShadowConfig(enabled=False, command=["echo", "x"])
    assert run_shadow(cfg) is None


def test_run_shadow_no_command_returns_none():
    cfg = ShadowConfig(enabled=True, command=[])
    assert run_shadow(cfg) is None


def test_run_shadow_success():
    cfg = ShadowConfig(enabled=True, command=[sys.executable, "-c", "exit(0)"], timeout=5.0)
    result = run_shadow(cfg)
    assert result is not None
    assert result.exit_code == 0
    assert not result.timed_out


def test_run_shadow_nonzero_exit():
    cfg = ShadowConfig(enabled=True, command=[sys.executable, "-c", "exit(1)"], timeout=5.0)
    result = run_shadow(cfg)
    assert result is not None
    assert result.exit_code == 1


def test_run_shadow_timeout():
    cfg = ShadowConfig(enabled=True, command=[sys.executable, "-c", "import time; time.sleep(10)"], timeout=0.05)
    result = run_shadow(cfg)
    assert result is not None
    assert result.timed_out is True


# ---------------------------------------------------------------------------
# compare_shadow
# ---------------------------------------------------------------------------

def test_compare_shadow_both_success():
    cfg = ShadowConfig(enabled=True, log_divergence=False)
    result = ShadowResult(exit_code=0, stdout="", stderr="")
    assert compare_shadow(0, result, cfg) is True


def test_compare_shadow_both_failure():
    cfg = ShadowConfig(enabled=True, log_divergence=False)
    result = ShadowResult(exit_code=2, stdout="", stderr="")
    assert compare_shadow(1, result, cfg) is True


def test_compare_shadow_diverges():
    cfg = ShadowConfig(enabled=True, log_divergence=False)
    result = ShadowResult(exit_code=1, stdout="", stderr="")
    assert compare_shadow(0, result, cfg) is False


def test_compare_shadow_timed_out_returns_false():
    cfg = ShadowConfig(enabled=True)
    result = ShadowResult(exit_code=None, stdout="", stderr="", timed_out=True)
    assert compare_shadow(0, result, cfg) is False


# ---------------------------------------------------------------------------
# middleware helpers
# ---------------------------------------------------------------------------

def test_parse_shadow_missing_section_uses_defaults():
    cfg = parse_shadow({})
    assert cfg.enabled is False


def test_parse_shadow_full_section():
    cfg = parse_shadow({"shadow": {"command": ["ls"], "timeout": 3.0}})
    assert cfg.command == ["ls"]
    assert cfg.timeout == 3.0


def test_parse_shadow_invalid_type_raises():
    with pytest.raises(TypeError):
        parse_shadow({"shadow": "bad"})


def test_shadow_config_to_dict_roundtrip():
    cfg = ShadowConfig(enabled=True, command=["foo"], timeout=7.0, log_divergence=False)
    d = shadow_config_to_dict(cfg)
    assert d["enabled"] is True
    assert d["command"] == ["foo"]
    assert d["timeout"] == 7.0
    assert d["log_divergence"] is False


def test_describe_shadow_disabled():
    cfg = ShadowConfig(enabled=False)
    assert "disabled" in describe_shadow(cfg)


def test_describe_shadow_enabled():
    cfg = ShadowConfig(enabled=True, command=["echo", "x"], timeout=5.0)
    desc = describe_shadow(cfg)
    assert "enabled" in desc
    assert "echo x" in desc


def test_maybe_run_shadow_disabled_returns_none():
    cfg = ShadowConfig(enabled=False)
    assert maybe_run_shadow(cfg, 0) is None
