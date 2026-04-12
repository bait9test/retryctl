"""Tests for retryctl.fallback and retryctl.fallback_middleware."""
from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from retryctl.fallback import FallbackConfig, FallbackResult, run_fallback
from retryctl.fallback_middleware import (
    describe_fallback,
    fallback_config_to_dict,
    maybe_run_fallback,
    parse_fallback,
)


# ---------------------------------------------------------------------------
# FallbackConfig.from_dict
# ---------------------------------------------------------------------------

def test_from_dict_defaults():
    cfg = FallbackConfig.from_dict({})
    assert cfg.enabled is False
    assert cfg.command == []
    assert cfg.timeout is None
    assert cfg.capture_output is True


def test_from_dict_full():
    cfg = FallbackConfig.from_dict(
        {"command": ["notify", "--fail"], "timeout": 5.0, "capture_output": False}
    )
    assert cfg.enabled is True
    assert cfg.command == ["notify", "--fail"]
    assert cfg.timeout == 5.0
    assert cfg.capture_output is False


def test_from_dict_string_command_splits():
    cfg = FallbackConfig.from_dict({"command": "echo hello"})
    assert cfg.command == ["echo", "hello"]
    assert cfg.enabled is True


def test_from_dict_explicit_disabled_overrides_command():
    cfg = FallbackConfig.from_dict({"command": ["echo", "hi"], "enabled": False})
    assert cfg.enabled is False


def test_from_dict_invalid_type_raises():
    with pytest.raises(TypeError):
        FallbackConfig.from_dict("not a dict")


def test_from_dict_invalid_command_type_raises():
    with pytest.raises(TypeError):
        FallbackConfig.from_dict({"command": 42})


def test_from_dict_zero_timeout_raises():
    with pytest.raises(ValueError):
        FallbackConfig.from_dict({"command": ["echo"], "timeout": 0})


# ---------------------------------------------------------------------------
# run_fallback
# ---------------------------------------------------------------------------

def test_run_fallback_disabled_returns_not_ran():
    cfg = FallbackConfig(enabled=False, command=["echo", "hi"])
    result = run_fallback(cfg)
    assert result.ran is False


def test_run_fallback_no_command_returns_not_ran():
    cfg = FallbackConfig(enabled=True, command=[])
    result = run_fallback(cfg)
    assert result.ran is False


def test_run_fallback_success():
    cfg = FallbackConfig(enabled=True, command=["echo", "ok"])
    mock_proc = MagicMock(returncode=0, stdout="ok\n", stderr="")
    with patch("subprocess.run", return_value=mock_proc):
        result = run_fallback(cfg)
    assert result.ran is True
    assert result.exit_code == 0
    assert result.stdout == "ok\n"


def test_run_fallback_nonzero_exit():
    cfg = FallbackConfig(enabled=True, command=["false"])
    mock_proc = MagicMock(returncode=1, stdout="", stderr="error")
    with patch("subprocess.run", return_value=mock_proc):
        result = run_fallback(cfg)
    assert result.exit_code == 1


def test_run_fallback_timeout():
    cfg = FallbackConfig(enabled=True, command=["sleep", "99"], timeout=0.01)
    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="sleep", timeout=0.01)):
        result = run_fallback(cfg)
    assert result.ran is True
    assert result.exit_code == -1
    assert "timeout" in result.stderr


def test_run_fallback_exception():
    cfg = FallbackConfig(enabled=True, command=["bad"])
    with patch("subprocess.run", side_effect=FileNotFoundError("bad")):
        result = run_fallback(cfg)
    assert result.exit_code == -1


# ---------------------------------------------------------------------------
# Middleware helpers
# ---------------------------------------------------------------------------

def test_parse_fallback_empty_config():
    cfg = parse_fallback({})
    assert cfg.enabled is False


def test_parse_fallback_full_section():
    cfg = parse_fallback({"fallback": {"command": ["notify"], "timeout": 3}})
    assert cfg.command == ["notify"]
    assert cfg.timeout == 3.0


def test_parse_fallback_invalid_section_raises():
    with pytest.raises(TypeError):
        parse_fallback({"fallback": "bad"})


def test_fallback_config_to_dict_roundtrip():
    cfg = FallbackConfig(enabled=True, command=["echo"], timeout=2.0, capture_output=False)
    d = fallback_config_to_dict(cfg)
    assert d["enabled"] is True
    assert d["command"] == ["echo"]
    assert d["timeout"] == 2.0
    assert d["capture_output"] is False


def test_maybe_run_fallback_skips_on_success():
    cfg = FallbackConfig(enabled=True, command=["echo", "hi"])
    metrics = MagicMock(succeeded=True)
    result = maybe_run_fallback(cfg, metrics)
    assert result.ran is False


def test_maybe_run_fallback_runs_on_failure():
    cfg = FallbackConfig(enabled=True, command=["echo", "hi"])
    metrics = MagicMock(succeeded=False)
    mock_proc = MagicMock(returncode=0, stdout="", stderr="")
    with patch("subprocess.run", return_value=mock_proc):
        result = maybe_run_fallback(cfg, metrics)
    assert result.ran is True


def test_describe_fallback_disabled():
    cfg = FallbackConfig(enabled=False)
    assert describe_fallback(cfg) == "fallback: disabled"


def test_describe_fallback_with_command():
    cfg = FallbackConfig(enabled=True, command=["notify", "--fail"])
    desc = describe_fallback(cfg)
    assert "notify --fail" in desc


def test_describe_fallback_with_timeout():
    cfg = FallbackConfig(enabled=True, command=["notify"], timeout=5.0)
    desc = describe_fallback(cfg)
    assert "timeout=5.0s" in desc
