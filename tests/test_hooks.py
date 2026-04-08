"""Tests for retryctl/hooks.py."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest

from retryctl.hooks import (
    HookConfig,
    dispatch_hooks,
    run_hook_command,
    run_post_hooks,
    run_pre_hooks,
)


# ---------------------------------------------------------------------------
# run_hook_command
# ---------------------------------------------------------------------------

def test_run_hook_command_success():
    ok = run_hook_command(f"{sys.executable} -c 'print(1)'", "test")
    assert ok is True


def test_run_hook_command_failure():
    ok = run_hook_command(f"{sys.executable} -c 'raise SystemExit(1)'", "test")
    assert ok is False


def test_run_hook_command_logs_stderr(caplog):
    import logging
    with caplog.at_level(logging.WARNING, logger="retryctl.hooks"):
        run_hook_command(
            f"{sys.executable} -c 'import sys; sys.stderr.write(\"oops\"); sys.exit(2)'",
            "pre",
        )
    assert "oops" in caplog.text


# ---------------------------------------------------------------------------
# dispatch_hooks
# ---------------------------------------------------------------------------

def test_dispatch_hooks_calls_all_callbacks():
    cb1 = MagicMock()
    cb2 = MagicMock()
    dispatch_hooks([cb1, cb2], "on_success")
    cb1.assert_called_once()
    cb2.assert_called_once()


def test_dispatch_hooks_continues_after_exception(caplog):
    import logging

    bad = MagicMock(side_effect=RuntimeError("boom"))
    good = MagicMock()

    with caplog.at_level(logging.ERROR, logger="retryctl.hooks"):
        dispatch_hooks([bad, good], "on_failure")

    good.assert_called_once()
    assert "boom" in caplog.text


# ---------------------------------------------------------------------------
# run_pre_hooks / run_post_hooks integration
# ---------------------------------------------------------------------------

def test_run_pre_hooks_no_command():
    """Should not raise even when pre_command is None."""
    cfg = HookConfig()
    run_pre_hooks(cfg)  # no exception


def test_run_pre_hooks_with_command():
    with patch("retryctl.hooks.run_hook_command", return_value=True) as mock_cmd:
        cfg = HookConfig(pre_command="echo hello")
        run_pre_hooks(cfg)
        mock_cmd.assert_called_once_with("echo hello", "pre")


def test_run_post_hooks_success_calls_on_success():
    cb = MagicMock()
    cfg = HookConfig(on_success=[cb])
    run_post_hooks(cfg, succeeded=True)
    cb.assert_called_once()


def test_run_post_hooks_failure_calls_on_failure():
    cb = MagicMock()
    cfg = HookConfig(on_failure=[cb])
    run_post_hooks(cfg, succeeded=False)
    cb.assert_called_once()


def test_run_post_hooks_success_does_not_call_on_failure():
    cb = MagicMock()
    cfg = HookConfig(on_failure=[cb])
    run_post_hooks(cfg, succeeded=True)
    cb.assert_not_called()


def test_run_post_hooks_with_post_command():
    with patch("retryctl.hooks.run_hook_command", return_value=True) as mock_cmd:
        cfg = HookConfig(post_command="echo done")
        run_post_hooks(cfg, succeeded=True)
        mock_cmd.assert_called_once_with("echo done", "post")
