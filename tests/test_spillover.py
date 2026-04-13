"""Tests for retryctl.spillover and retryctl.spillover_middleware."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from retryctl.spillover import SpilloverConfig, SpilloverResult, run_spillover
from retryctl.spillover_middleware import (
    describe_spillover,
    maybe_run_spillover,
    parse_spillover,
    spillover_config_to_dict,
)


# ---------------------------------------------------------------------------
# Config parsing
# ---------------------------------------------------------------------------

def test_config_defaults():
    cfg = SpilloverConfig()
    assert cfg.enabled is False
    assert cfg.threshold == 3
    assert cfg.command == []
    assert cfg.capture_output is True
    assert cfg.timeout is None


def test_from_dict_full():
    cfg = SpilloverConfig.from_dict({
        "enabled": True,
        "threshold": 5,
        "command": ["notify", "--overflow"],
        "capture_output": False,
        "timeout": 10.0,
    })
    assert cfg.enabled is True
    assert cfg.threshold == 5
    assert cfg.command == ["notify", "--overflow"]
    assert cfg.capture_output is False
    assert cfg.timeout == 10.0


def test_from_dict_string_command_splits():
    cfg = SpilloverConfig.from_dict({"command": "notify --overflow"})
    assert cfg.command == ["notify", "--overflow"]
    assert cfg.enabled is True  # auto-enabled because command is set


def test_from_dict_auto_enables_when_command_set():
    cfg = SpilloverConfig.from_dict({"command": ["echo", "hi"]})
    assert cfg.enabled is True


def test_from_dict_explicit_disabled_overrides_command():
    cfg = SpilloverConfig.from_dict({"enabled": False, "command": ["echo", "hi"]})
    assert cfg.enabled is False


def test_from_dict_invalid_type_raises():
    with pytest.raises(TypeError):
        SpilloverConfig.from_dict("not-a-dict")


def test_from_dict_invalid_command_type_raises():
    with pytest.raises(TypeError):
        SpilloverConfig.from_dict({"command": 42})


def test_from_dict_zero_threshold_raises():
    with pytest.raises(ValueError):
        SpilloverConfig.from_dict({"threshold": 0})


def test_from_dict_negative_timeout_raises():
    with pytest.raises(ValueError):
        SpilloverConfig.from_dict({"command": ["echo"], "timeout": -1})


# ---------------------------------------------------------------------------
# run_spillover logic
# ---------------------------------------------------------------------------

def test_not_triggered_below_threshold():
    cfg = SpilloverConfig(enabled=True, threshold=3, command=["echo"])
    result = run_spillover(cfg, attempt=2, original_command=["myapp"])
    assert result.triggered is False


def test_not_triggered_when_disabled():
    cfg = SpilloverConfig(enabled=False, threshold=1, command=["echo"])
    result = run_spillover(cfg, attempt=5, original_command=["myapp"])
    assert result.triggered is False


def test_triggered_at_threshold():
    cfg = SpilloverConfig(enabled=True, threshold=3, command=["echo", "overflow"])
    with patch("retryctl.spillover.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")
        result = run_spillover(cfg, attempt=3, original_command=["myapp"])
    assert result.triggered is True
    assert result.returncode == 0


def test_triggered_above_threshold():
    cfg = SpilloverConfig(enabled=True, threshold=2, command=["echo"])
    with patch("retryctl.spillover.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        result = run_spillover(cfg, attempt=10, original_command=["myapp"])
    assert result.triggered is True


def test_triggered_no_command_returns_triggered_no_rc():
    cfg = SpilloverConfig(enabled=True, threshold=1, command=[])
    result = run_spillover(cfg, attempt=1, original_command=["myapp"])
    assert result.triggered is True
    assert result.returncode is None


def test_timeout_returns_rc_minus_one():
    import subprocess
    cfg = SpilloverConfig(enabled=True, threshold=1, command=["sleep", "99"], timeout=0.001)
    with patch("retryctl.spillover.subprocess.run", side_effect=subprocess.TimeoutExpired("sleep", 0.001)):
        result = run_spillover(cfg, attempt=1, original_command=["myapp"])
    assert result.triggered is True
    assert result.returncode == -1


# ---------------------------------------------------------------------------
# Middleware helpers
# ---------------------------------------------------------------------------

def test_parse_spillover_missing_section_uses_defaults():
    cfg = parse_spillover({})
    assert cfg.enabled is False


def test_parse_spillover_full_section():
    cfg = parse_spillover({"spillover": {"threshold": 2, "command": ["alert"]}})
    assert cfg.threshold == 2
    assert cfg.command == ["alert"]


def test_parse_spillover_invalid_section_type_raises():
    with pytest.raises(TypeError):
        parse_spillover({"spillover": "bad"})


def test_spillover_config_to_dict_roundtrip():
    cfg = SpilloverConfig(enabled=True, threshold=4, command=["x"], capture_output=False, timeout=5.0)
    d = spillover_config_to_dict(cfg)
    assert d["threshold"] == 4
    assert d["command"] == ["x"]
    assert d["timeout"] == 5.0


def test_describe_spillover_disabled():
    assert "disabled" in describe_spillover(SpilloverConfig())


def test_describe_spillover_enabled():
    cfg = SpilloverConfig(enabled=True, threshold=3, command=["notify"])
    desc = describe_spillover(cfg)
    assert "threshold=3" in desc
    assert "notify" in desc


def test_maybe_run_spillover_not_triggered():
    cfg = SpilloverConfig(enabled=True, threshold=5, command=["echo"])
    result = maybe_run_spillover(cfg, attempt=2, original_command=["app"])
    assert result.triggered is False
