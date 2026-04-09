"""Tests for retryctl.notify and retryctl.notify_hook."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from retryctl.notify import (
    NotifyConfig,
    NotifyLevel,
    _build_cmd,
    _notifier_cmd,
    send_notification,
)
from retryctl.notify_hook import _build_message, notify_on_finish


# ---------------------------------------------------------------------------
# NotifyConfig
# ---------------------------------------------------------------------------

def test_notify_config_defaults():
    cfg = NotifyConfig()
    assert cfg.level == NotifyLevel.NEVER
    assert cfg.title == "retryctl"
    assert cfg.sound is False
    assert cfg.extra_args == []


def test_notify_config_from_dict():
    cfg = NotifyConfig.from_dict({"level": "failure", "title": "MyApp", "sound": True})
    assert cfg.level == NotifyLevel.FAILURE
    assert cfg.title == "MyApp"
    assert cfg.sound is True


def test_notify_config_from_dict_invalid_level():
    with pytest.raises(ValueError):
        NotifyConfig.from_dict({"level": "bogus"})


# ---------------------------------------------------------------------------
# _build_cmd
# ---------------------------------------------------------------------------

def test_build_cmd_notify_send():
    cfg = NotifyConfig(title="T", sound=False)
    cmd = _build_cmd("notify-send", cfg, "hello")
    assert cmd[:3] == ["notify-send", "T", "hello"]


def test_build_cmd_notify_send_sound_adds_urgency():
    cfg = NotifyConfig(title="T", sound=True)
    cmd = _build_cmd("notify-send", cfg, "msg")
    assert "--urgency" in cmd


def test_build_cmd_terminal_notifier():
    cfg = NotifyConfig(title="TN", sound=True)
    cmd = _build_cmd("terminal-notifier", cfg, "msg")
    assert "-sound" in cmd
    assert "default" in cmd


def test_build_cmd_osascript_fallback():
    cfg = NotifyConfig(title="OS")
    cmd = _build_cmd("osascript", cfg, "done")
    assert cmd[0] == "osascript"
    assert "done" in cmd[-1]


def test_build_cmd_appends_extra_args():
    cfg = NotifyConfig(extra_args=["--expire-time", "3000"])
    cmd = _build_cmd("notify-send", cfg, "x")
    assert "--expire-time" in cmd
    assert "3000" in cmd


# ---------------------------------------------------------------------------
# send_notification
# ---------------------------------------------------------------------------

def test_send_notification_never_returns_false():
    cfg = NotifyConfig(level=NotifyLevel.NEVER)
    assert send_notification(cfg, "msg", success=True) is False


def test_send_notification_failure_skips_on_success():
    cfg = NotifyConfig(level=NotifyLevel.FAILURE)
    assert send_notification(cfg, "msg", success=True) is False


def test_send_notification_failure_fires_on_failure():
    cfg = NotifyConfig(level=NotifyLevel.FAILURE)
    with patch("retryctl.notify._notifier_cmd", return_value="notify-send"), \
         patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        result = send_notification(cfg, "msg", success=False)
    assert result is True


def test_send_notification_no_binary_returns_false():
    cfg = NotifyConfig(level=NotifyLevel.ALWAYS)
    with patch("retryctl.notify._notifier_cmd", return_value=None):
        assert send_notification(cfg, "msg", success=True) is False


def test_send_notification_subprocess_error_returns_false():
    cfg = NotifyConfig(level=NotifyLevel.ALWAYS)
    with patch("retryctl.notify._notifier_cmd", return_value="notify-send"), \
         patch("subprocess.run", side_effect=OSError("boom")):
        assert send_notification(cfg, "msg", success=True) is False


# ---------------------------------------------------------------------------
# notify_hook helpers
# ---------------------------------------------------------------------------

def _make_metrics(succeeded: bool, attempts: int):
    m = MagicMock()
    m.succeeded = succeeded
    m.total_attempts = attempts
    return m


def test_build_message_success():
    msg = _build_message(_make_metrics(True, 1), "echo hi")
    assert "succeeded" in msg
    assert "1 attempt" in msg


def test_build_message_failure_plural():
    msg = _build_message(_make_metrics(False, 3), "false")
    assert "failed" in msg
    assert "3 attempts" in msg


def test_build_message_truncates_long_command():
    long_cmd = "x" * 80
    msg = _build_message(_make_metrics(True, 1), long_cmd)
    assert "..." in msg


def test_notify_on_finish_none_config_does_nothing():
    # Should not raise
    notify_on_finish(None, _make_metrics(True, 1), "echo")


def test_notify_on_finish_delegates_to_send():
    cfg = NotifyConfig(level=NotifyLevel.ALWAYS)
    with patch("retryctl.notify_hook.send_notification", return_value=True) as mock_send:
        notify_on_finish(cfg, _make_metrics(False, 2), "false")
    mock_send.assert_called_once()
    _, call_msg, call_success = mock_send.call_args[0]
    assert "failed" in call_msg
    assert call_success is False
