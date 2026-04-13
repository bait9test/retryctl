"""Tests for retryctl.fence."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from retryctl.fence import FenceConfig, FenceBlocked, check_fence


# ---------------------------------------------------------------------------
# FenceConfig.from_dict
# ---------------------------------------------------------------------------

def test_config_defaults():
    cfg = FenceConfig()
    assert cfg.enabled is False
    assert cfg.command == []
    assert cfg.timeout == 10.0
    assert cfg.on_fail == "block"


def test_from_dict_empty_uses_defaults():
    cfg = FenceConfig.from_dict({})
    assert cfg.enabled is False
    assert cfg.command == []


def test_from_dict_string_command_splits():
    cfg = FenceConfig.from_dict({"command": "echo hello"})
    assert cfg.command == ["echo", "hello"]
    assert cfg.enabled is True  # auto-enabled when command provided


def test_from_dict_list_command():
    cfg = FenceConfig.from_dict({"command": ["ping", "-c1", "localhost"]})
    assert cfg.command == ["ping", "-c1", "localhost"]


def test_from_dict_explicit_disabled_overrides_command():
    cfg = FenceConfig.from_dict({"command": "echo hi", "enabled": False})
    assert cfg.enabled is False


def test_from_dict_invalid_type_raises():
    with pytest.raises(TypeError):
        FenceConfig.from_dict("not a dict")


def test_from_dict_invalid_command_type_raises():
    with pytest.raises(TypeError):
        FenceConfig.from_dict({"command": 123})


def test_from_dict_invalid_on_fail_raises():
    with pytest.raises(ValueError, match="on_fail"):
        FenceConfig.from_dict({"command": "true", "on_fail": "explode"})


def test_from_dict_zero_timeout_raises():
    with pytest.raises(ValueError, match="timeout"):
        FenceConfig.from_dict({"command": "true", "timeout": 0})


def test_from_dict_full():
    cfg = FenceConfig.from_dict({
        "command": ["check_db"],
        "timeout": 5.0,
        "on_fail": "warn",
        "enabled": True,
    })
    assert cfg.command == ["check_db"]
    assert cfg.timeout == 5.0
    assert cfg.on_fail == "warn"
    assert cfg.enabled is True


# ---------------------------------------------------------------------------
# check_fence
# ---------------------------------------------------------------------------

def test_disabled_fence_always_passes():
    cfg = FenceConfig(enabled=False, command=["false"])
    assert check_fence(cfg) is True


def test_empty_command_always_passes():
    cfg = FenceConfig(enabled=True, command=[])
    assert check_fence(cfg) is True


def _make_cfg(on_fail="block", cmd=None):
    return FenceConfig(enabled=True, command=cmd or ["check"], timeout=5.0, on_fail=on_fail)


def test_passing_fence_returns_true():
    cfg = _make_cfg()
    mock_result = MagicMock(returncode=0, stderr=b"")
    with patch("retryctl.fence.subprocess.run", return_value=mock_result):
        assert check_fence(cfg) is True


def test_failing_fence_block_raises():
    cfg = _make_cfg(on_fail="block")
    mock_result = MagicMock(returncode=1, stderr=b"")
    with patch("retryctl.fence.subprocess.run", return_value=mock_result):
        with pytest.raises(FenceBlocked) as exc_info:
            check_fence(cfg)
    assert exc_info.value.returncode == 1


def test_failing_fence_warn_returns_false():
    cfg = _make_cfg(on_fail="warn")
    mock_result = MagicMock(returncode=2, stderr=b"")
    with patch("retryctl.fence.subprocess.run", return_value=mock_result):
        assert check_fence(cfg) is False


def test_failing_fence_skip_returns_true():
    cfg = _make_cfg(on_fail="skip")
    mock_result = MagicMock(returncode=1, stderr=b"")
    with patch("retryctl.fence.subprocess.run", return_value=mock_result):
        assert check_fence(cfg) is True


def test_timeout_treated_as_failure_block():
    import subprocess as sp
    cfg = _make_cfg(on_fail="block")
    with patch("retryctl.fence.subprocess.run", side_effect=sp.TimeoutExpired(cmd="check", timeout=5)):
        with pytest.raises(FenceBlocked):
            check_fence(cfg)


def test_oserror_treated_as_failure_warn():
    cfg = _make_cfg(on_fail="warn")
    with patch("retryctl.fence.subprocess.run", side_effect=OSError("no such file")):
        assert check_fence(cfg) is False
