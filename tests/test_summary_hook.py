"""Tests for retryctl.summary_hook.finalize_run."""

from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch, call

import pytest

from retryctl.metrics import RunMetrics, record_attempt, finish
from retryctl.summary_hook import finalize_run


def _make_metrics(succeeded: bool = True) -> RunMetrics:
    m = RunMetrics()
    m.started_at = 0.0
    m.ended_at = 1.0
    record_attempt(m, exit_code=0 if succeeded else 1, succeeded=succeeded, delay_before=None)
    finish(m, succeeded=succeeded)
    return m


# ---------------------------------------------------------------------------
# basic smoke tests
# ---------------------------------------------------------------------------

def test_finalize_run_logs_summary(caplog):
    m = _make_metrics(succeeded=True)
    with caplog.at_level(logging.INFO, logger="retryctl.reporter"):
        finalize_run(metrics=m, command="echo hi")
    assert "succeeded" in caplog.text


def test_finalize_run_no_hooks_no_alerts():
    """Should not raise when hook_config and alert_config are both None."""
    m = _make_metrics(succeeded=False)
    finalize_run(metrics=m, command="false", exit_code=1)


# ---------------------------------------------------------------------------
# hook integration
# ---------------------------------------------------------------------------

def test_finalize_run_calls_post_hooks():
    m = _make_metrics(succeeded=True)
    with patch("retryctl.summary_hook.run_post_hooks") as mock_hooks:
        hook_cfg = MagicMock()
        finalize_run(metrics=m, command="cmd", hook_config=hook_cfg, exit_code=0)
        mock_hooks.assert_called_once_with(hook_cfg, exit_code=0, succeeded=True)


def test_finalize_run_hook_exception_does_not_propagate(caplog):
    m = _make_metrics(succeeded=True)
    with patch("retryctl.summary_hook.run_post_hooks", side_effect=RuntimeError("boom")):
        hook_cfg = MagicMock()
        with caplog.at_level(logging.ERROR, logger="retryctl.summary_hook"):
            finalize_run(metrics=m, command="cmd", hook_config=hook_cfg)
        assert "post-hook" in caplog.text


# ---------------------------------------------------------------------------
# alert integration
# ---------------------------------------------------------------------------

def test_finalize_run_calls_dispatch_alert():
    m = _make_metrics(succeeded=False)
    with patch("retryctl.summary_hook.dispatch_alert") as mock_alert:
        alert_cfg = MagicMock()
        finalize_run(metrics=m, command="bad", alert_config=alert_cfg, exit_code=1)
        assert mock_alert.called
        ctx_arg = mock_alert.call_args[0][1]
        assert ctx_arg.command == "bad"
        assert ctx_arg.succeeded is False


def test_finalize_run_alert_exception_does_not_propagate(caplog):
    m = _make_metrics(succeeded=True)
    with patch("retryctl.summary_hook.dispatch_alert", side_effect=RuntimeError("oops")):
        alert_cfg = MagicMock()
        with caplog.at_level(logging.ERROR, logger="retryctl.summary_hook"):
            finalize_run(metrics=m, command="cmd", alert_config=alert_cfg)
        assert "alert dispatch" in caplog.text


def test_finalize_run_alert_body_in_extra():
    m = _make_metrics(succeeded=True)
    captured_ctx = {}

    def _fake_dispatch(cfg, ctx):
        captured_ctx["ctx"] = ctx

    with patch("retryctl.summary_hook.dispatch_alert", side_effect=_fake_dispatch):
        finalize_run(metrics=m, command="myapp", alert_config=MagicMock())

    assert "body" in captured_ctx["ctx"].extra
    assert "myapp" in captured_ctx["ctx"].extra["body"]
