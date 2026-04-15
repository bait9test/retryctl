"""Tests for retryctl.canary and retryctl.canary_middleware."""
from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from retryctl.canary import CanaryBlocked, CanaryConfig, run_canary
from retryctl.canary_middleware import (
    before_attempt,
    canary_config_to_dict,
    describe_canary,
    parse_canary,
)


# ---------------------------------------------------------------------------
# CanaryConfig.from_dict
# ---------------------------------------------------------------------------

def test_config_defaults():
    cfg = CanaryConfig.from_dict({})
    assert cfg.enabled is False
    assert cfg.command == []
    assert cfg.timeout == 5.0
    assert cfg.skip_on_failure is True


def test_config_from_dict_full():
    cfg = CanaryConfig.from_dict(
        {"command": ["ping", "-c1", "localhost"], "timeout": 3.0, "skip_on_failure": False}
    )
    assert cfg.enabled is True
    assert cfg.command == ["ping", "-c1", "localhost"]
    assert cfg.timeout == 3.0
    assert cfg.skip_on_failure is False


def test_config_string_command_splits():
    cfg = CanaryConfig.from_dict({"command": "echo hello"})
    assert cfg.command == ["echo", "hello"]
    assert cfg.enabled is True


def test_config_auto_enables_when_command_set():
    cfg = CanaryConfig.from_dict({"command": ["true"]})
    assert cfg.enabled is True


def test_config_explicit_disabled_overrides_command():
    cfg = CanaryConfig.from_dict({"command": ["true"], "enabled": False})
    assert cfg.enabled is False


def test_config_invalid_type_raises():
    with pytest.raises(TypeError):
        CanaryConfig.from_dict("not-a-dict")  # type: ignore[arg-type]


def test_config_invalid_command_type_raises():
    with pytest.raises(TypeError):
        CanaryConfig.from_dict({"command": 42})


def test_config_zero_timeout_raises():
    with pytest.raises(ValueError):
        CanaryConfig.from_dict({"command": ["true"], "timeout": 0})


# ---------------------------------------------------------------------------
# run_canary
# ---------------------------------------------------------------------------

def _cfg(skip=True, cmd=None):
    return CanaryConfig(
        enabled=True,
        command=cmd or ["true"],
        timeout=2.0,
        skip_on_failure=skip,
    )


def test_run_canary_disabled_returns_true():
    cfg = CanaryConfig()  # enabled=False
    assert run_canary(cfg) is True


def test_run_canary_passes():
    mock_result = MagicMock(returncode=0)
    with patch("retryctl.canary.subprocess.run", return_value=mock_result):
        assert run_canary(_cfg()) is True


def test_run_canary_fails_skip_returns_false():
    mock_result = MagicMock(returncode=1)
    with patch("retryctl.canary.subprocess.run", return_value=mock_result):
        assert run_canary(_cfg(skip=True)) is False


def test_run_canary_fails_abort_raises():
    mock_result = MagicMock(returncode=1)
    with patch("retryctl.canary.subprocess.run", return_value=mock_result):
        with pytest.raises(CanaryBlocked) as exc_info:
            run_canary(_cfg(skip=False))
    assert exc_info.value.returncode == 1


def test_run_canary_timeout_skip_returns_false():
    with patch("retryctl.canary.subprocess.run", side_effect=subprocess.TimeoutExpired("true", 2)):
        assert run_canary(_cfg(skip=True)) is False


def test_run_canary_timeout_abort_raises():
    with patch("retryctl.canary.subprocess.run", side_effect=subprocess.TimeoutExpired("true", 2)):
        with pytest.raises(CanaryBlocked):
            run_canary(_cfg(skip=False))


# ---------------------------------------------------------------------------
# middleware helpers
# ---------------------------------------------------------------------------

def test_parse_canary_missing_section_uses_defaults():
    cfg = parse_canary({})
    assert cfg.enabled is False


def test_parse_canary_full_section():
    cfg = parse_canary({"canary": {"command": ["curl", "http://health"], "timeout": 1.5}})
    assert cfg.command == ["curl", "http://health"]
    assert cfg.timeout == 1.5


def test_parse_canary_invalid_type_raises():
    with pytest.raises(TypeError):
        parse_canary({"canary": "bad"})


def test_canary_config_to_dict_roundtrip():
    cfg = CanaryConfig.from_dict({"command": ["true"], "timeout": 2.0, "skip_on_failure": False})
    d = canary_config_to_dict(cfg)
    assert d["command"] == ["true"]
    assert d["timeout"] == 2.0
    assert d["skip_on_failure"] is False


def test_before_attempt_disabled_always_true():
    cfg = CanaryConfig()  # disabled
    assert before_attempt(cfg, 1) is True


def test_before_attempt_passes_when_canary_healthy():
    mock_result = MagicMock(returncode=0)
    with patch("retryctl.canary.subprocess.run", return_value=mock_result):
        assert before_attempt(_cfg(), 1) is True


def test_before_attempt_returns_false_when_canary_fails_skip():
    mock_result = MagicMock(returncode=1)
    with patch("retryctl.canary.subprocess.run", return_value=mock_result):
        assert before_attempt(_cfg(skip=True), 2) is False


def test_describe_canary_disabled():
    assert "disabled" in describe_canary(CanaryConfig())


def test_describe_canary_enabled():
    cfg = _cfg(skip=False, cmd=["curl", "http://health"])
    desc = describe_canary(cfg)
    assert "curl" in desc
    assert "abort" in desc
