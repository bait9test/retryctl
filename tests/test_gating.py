"""Tests for retryctl.gating and retryctl.gating_middleware."""
from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from retryctl.gating import GatingConfig, GateBlocked, check_gate
from retryctl.gating_middleware import (
    before_attempt,
    describe_gating,
    gating_config_to_dict,
    parse_gating,
)


# ---------------------------------------------------------------------------
# GatingConfig.from_dict
# ---------------------------------------------------------------------------

def test_config_defaults():
    cfg = GatingConfig.from_dict({})
    assert cfg.enabled is False
    assert cfg.command == []
    assert cfg.timeout == 10.0
    assert cfg.allow_on_error is True


def test_config_from_dict_full():
    cfg = GatingConfig.from_dict(
        {"command": ["sh", "-c", "exit 0"], "timeout": 5.0, "allow_on_error": False, "enabled": True}
    )
    assert cfg.enabled is True
    assert cfg.command == ["sh", "-c", "exit 0"]
    assert cfg.timeout == 5.0
    assert cfg.allow_on_error is False


def test_config_string_command_splits():
    cfg = GatingConfig.from_dict({"command": "echo hello"})
    assert cfg.command == ["echo", "hello"]
    assert cfg.enabled is True  # auto-enabled because command is set


def test_config_invalid_type_raises():
    with pytest.raises(TypeError):
        GatingConfig.from_dict("bad")


def test_config_invalid_command_type_raises():
    with pytest.raises(TypeError):
        GatingConfig.from_dict({"command": 42})


def test_config_zero_timeout_raises():
    with pytest.raises(ValueError):
        GatingConfig.from_dict({"command": ["true"], "timeout": 0})


# ---------------------------------------------------------------------------
# check_gate
# ---------------------------------------------------------------------------

def test_disabled_gate_does_nothing():
    cfg = GatingConfig(enabled=False, command=["false"])
    check_gate(cfg)  # should not raise


def test_gate_passes_on_exit_zero():
    cfg = GatingConfig(enabled=True, command=["true"], timeout=5.0)
    check_gate(cfg)  # should not raise


def test_gate_blocks_on_nonzero():
    cfg = GatingConfig(enabled=True, command=["false"], timeout=5.0)
    with pytest.raises(GateBlocked) as exc_info:
        check_gate(cfg)
    assert exc_info.value.exit_code == 1


def test_gate_allows_on_error_when_flag_set():
    cfg = GatingConfig(enabled=True, command=["nonexistent_cmd_xyz"], timeout=5.0, allow_on_error=True)
    check_gate(cfg)  # should not raise


def test_gate_raises_on_error_when_flag_unset():
    cfg = GatingConfig(enabled=True, command=["nonexistent_cmd_xyz"], timeout=5.0, allow_on_error=False)
    with pytest.raises(GateBlocked):
        check_gate(cfg)


# ---------------------------------------------------------------------------
# middleware helpers
# ---------------------------------------------------------------------------

def test_parse_gating_empty_config():
    cfg = parse_gating({})
    assert cfg.enabled is False


def test_parse_gating_full_section():
    cfg = parse_gating({"gating": {"command": ["true"], "timeout": 3.0}})
    assert cfg.command == ["true"]
    assert cfg.timeout == 3.0


def test_parse_gating_invalid_section_raises():
    with pytest.raises(TypeError):
        parse_gating({"gating": "bad"})


def test_gating_config_to_dict_roundtrip():
    cfg = GatingConfig(enabled=True, command=["echo", "ok"], timeout=7.0, allow_on_error=False)
    d = gating_config_to_dict(cfg)
    cfg2 = GatingConfig.from_dict(d)
    assert cfg2.enabled == cfg.enabled
    assert cfg2.command == cfg.command
    assert cfg2.timeout == cfg.timeout
    assert cfg2.allow_on_error == cfg.allow_on_error


def test_before_attempt_disabled_skips():
    cfg = GatingConfig(enabled=False, command=["false"])
    before_attempt(cfg, 1)  # must not raise


def test_before_attempt_raises_when_blocked():
    cfg = GatingConfig(enabled=True, command=["false"], timeout=5.0)
    with pytest.raises(GateBlocked):
        before_attempt(cfg, 1)


def test_describe_gating_disabled():
    cfg = GatingConfig()
    assert "disabled" in describe_gating(cfg)


def test_describe_gating_enabled():
    cfg = GatingConfig(enabled=True, command=["my-check"], timeout=4.0)
    desc = describe_gating(cfg)
    assert "my-check" in desc
    assert "4.0" in desc
