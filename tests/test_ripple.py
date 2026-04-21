"""Tests for retryctl.ripple and retryctl.ripple_middleware."""
from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from retryctl.ripple import RippleConfig, fire_ripple
from retryctl.ripple_middleware import (
    describe_ripple,
    on_run_complete,
    parse_ripple,
    ripple_config_to_dict,
)


# ---------------------------------------------------------------------------
# RippleConfig.from_dict
# ---------------------------------------------------------------------------

def test_config_defaults():
    cfg = RippleConfig.from_dict({})
    assert cfg.enabled is False
    assert cfg.command == []
    assert cfg.on_failure is True
    assert cfg.on_success is False
    assert cfg.timeout == 10.0


def test_config_from_dict_full():
    cfg = RippleConfig.from_dict({
        "enabled": True,
        "command": ["curl", "-X", "POST", "http://example.com/hook"],
        "on_failure": True,
        "on_success": True,
        "timeout": 5.0,
    })
    assert cfg.enabled is True
    assert cfg.command == ["curl", "-X", "POST", "http://example.com/hook"]
    assert cfg.on_success is True
    assert cfg.timeout == 5.0


def test_config_string_command_splits():
    cfg = RippleConfig.from_dict({"command": "notify-send 'done'"})
    assert cfg.command == ["notify-send", "done"]
    assert cfg.enabled is True  # auto-enabled when command present


def test_config_auto_enables_when_command_set():
    cfg = RippleConfig.from_dict({"command": ["echo", "hi"]})
    assert cfg.enabled is True


def test_config_explicit_disabled_overrides_command():
    cfg = RippleConfig.from_dict({"command": ["echo", "hi"], "enabled": False})
    assert cfg.enabled is False


def test_config_invalid_type_raises():
    with pytest.raises(TypeError, match="ripple"):
        RippleConfig.from_dict("bad")


def test_config_invalid_command_type_raises():
    with pytest.raises(TypeError, match="command"):
        RippleConfig.from_dict({"command": 42})


# ---------------------------------------------------------------------------
# fire_ripple
# ---------------------------------------------------------------------------

def _make_cfg(**kwargs) -> RippleConfig:
    defaults = {"enabled": True, "command": ["echo", "ripple"], "on_failure": True, "on_success": False, "timeout": 5.0}
    defaults.update(kwargs)
    return RippleConfig(**defaults)


def test_fire_ripple_disabled_does_nothing():
    cfg = _make_cfg(enabled=False)
    with patch("subprocess.run") as mock_run:
        fire_ripple(cfg, succeeded=False)
        mock_run.assert_not_called()


def test_fire_ripple_no_command_does_nothing():
    cfg = _make_cfg(command=[])
    with patch("subprocess.run") as mock_run:
        fire_ripple(cfg, succeeded=False)
        mock_run.assert_not_called()


def test_fire_ripple_on_failure_fires():
    cfg = _make_cfg(on_failure=True)
    mock_result = MagicMock(returncode=0, stderr="")
    with patch("subprocess.run", return_value=mock_result) as mock_run:
        fire_ripple(cfg, succeeded=False)
        mock_run.assert_called_once()


def test_fire_ripple_skips_success_when_not_configured():
    cfg = _make_cfg(on_success=False)
    with patch("subprocess.run") as mock_run:
        fire_ripple(cfg, succeeded=True)
        mock_run.assert_not_called()


def test_fire_ripple_fires_on_success_when_configured():
    cfg = _make_cfg(on_success=True)
    mock_result = MagicMock(returncode=0, stderr="")
    with patch("subprocess.run", return_value=mock_result) as mock_run:
        fire_ripple(cfg, succeeded=True)
        mock_run.assert_called_once()


def test_fire_ripple_logs_warning_on_nonzero(caplog):
    cfg = _make_cfg()
    mock_result = MagicMock(returncode=1, stderr="oops")
    with patch("subprocess.run", return_value=mock_result):
        import logging
        with caplog.at_level(logging.WARNING, logger="retryctl.ripple"):
            fire_ripple(cfg, succeeded=False)
    assert "exited 1" in caplog.text


def test_fire_ripple_timeout_logs_warning(caplog):
    cfg = _make_cfg()
    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="echo", timeout=5)):
        import logging
        with caplog.at_level(logging.WARNING, logger="retryctl.ripple"):
            fire_ripple(cfg, succeeded=False)
    assert "timed out" in caplog.text


# ---------------------------------------------------------------------------
# middleware helpers
# ---------------------------------------------------------------------------

def test_parse_ripple_empty_config_uses_defaults():
    cfg = parse_ripple({})
    assert cfg.enabled is False


def test_parse_ripple_full_section():
    cfg = parse_ripple({"ripple": {"command": ["curl", "http://x"], "on_success": True}})
    assert cfg.enabled is True
    assert cfg.on_success is True


def test_parse_ripple_invalid_type_raises():
    with pytest.raises(TypeError):
        parse_ripple({"ripple": "bad"})


def test_ripple_config_to_dict_roundtrip():
    cfg = _make_cfg(on_success=True, timeout=3.0)
    d = ripple_config_to_dict(cfg)
    cfg2 = RippleConfig(**d)
    assert cfg2.on_success is True
    assert cfg2.timeout == 3.0


def test_on_run_complete_delegates():
    cfg = _make_cfg()
    with patch("retryctl.ripple_middleware.fire_ripple") as mock_fire:
        on_run_complete(cfg, succeeded=False)
        mock_fire.assert_called_once_with(cfg, succeeded=False)


def test_describe_ripple_disabled():
    cfg = _make_cfg(enabled=False)
    assert "disabled" in describe_ripple(cfg)


def test_describe_ripple_enabled():
    cfg = _make_cfg(on_failure=True, on_success=True)
    desc = describe_ripple(cfg)
    assert "failure" in desc
    assert "success" in desc
