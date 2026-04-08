"""Tests for retryctl.reporter."""

from __future__ import annotations

import time
import pytest

from retryctl.metrics import RunMetrics, record_attempt, finish
from retryctl.reporter import _duration_str, build_summary, log_summary, alert_body


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _make_metrics(attempts=None, succeeded=True) -> RunMetrics:
    m = RunMetrics()
    m.started_at = 0.0
    m.ended_at = 5.5
    for code, delay in (attempts or [(0, None)]):
        record_attempt(m, exit_code=code, succeeded=(code == 0), delay_before=delay)
    finish(m, succeeded=succeeded)
    return m


# ---------------------------------------------------------------------------
# _duration_str
# ---------------------------------------------------------------------------

def test_duration_str_seconds_only():
    assert _duration_str(45) == "45s"


def test_duration_str_minutes_and_seconds():
    assert _duration_str(125) == "2m 5s"


def test_duration_str_hours_minutes_seconds():
    assert _duration_str(3661) == "1h 1m 1s"


def test_duration_str_zero():
    assert _duration_str(0) == "0s"


# ---------------------------------------------------------------------------
# build_summary
# ---------------------------------------------------------------------------

def test_build_summary_success():
    m = _make_metrics(attempts=[(0, None)], succeeded=True)
    s = build_summary(m, "echo hello")
    assert s["command"] == "echo hello"
    assert s["succeeded"] is True
    assert s["total_attempts"] == 1
    assert s["failed_attempts"] == 0


def test_build_summary_failure_counts():
    m = _make_metrics(attempts=[(1, 1.0), (1, 2.0), (1, None)], succeeded=False)
    s = build_summary(m, "false")
    assert s["failed_attempts"] == 3
    assert s["exit_codes"] == [1, 1, 1]


def test_build_summary_delays_filtered():
    m = _make_metrics(attempts=[(1, 1.5), (0, None)], succeeded=True)
    s = build_summary(m, "cmd")
    assert s["delays"] == [1.5]


def test_build_summary_duration():
    m = _make_metrics(attempts=[(0, None)], succeeded=True)
    s = build_summary(m, "cmd")
    assert s["duration_seconds"] == 5.5
    assert "5s" in s["duration_human"]


# ---------------------------------------------------------------------------
# log_summary
# ---------------------------------------------------------------------------

def test_log_summary_success(caplog):
    import logging
    m = _make_metrics(attempts=[(0, None)], succeeded=True)
    with caplog.at_level(logging.INFO, logger="retryctl.reporter"):
        log_summary(m, "echo ok")
    assert "succeeded" in caplog.text


def test_log_summary_failure_warns(caplog):
    import logging
    m = _make_metrics(attempts=[(2, None), (2, None)], succeeded=False)
    with caplog.at_level(logging.WARNING, logger="retryctl.reporter"):
        log_summary(m, "bad-cmd")
    assert "failed" in caplog.text.lower()


# ---------------------------------------------------------------------------
# alert_body
# ---------------------------------------------------------------------------

def test_alert_body_contains_command():
    m = _make_metrics(attempts=[(1, 0.5)], succeeded=False)
    body = alert_body(m, "my-command --flag")
    assert "my-command --flag" in body


def test_alert_body_failed_label():
    m = _make_metrics(attempts=[(1, None)], succeeded=False)
    body = alert_body(m, "cmd")
    assert "FAILED" in body


def test_alert_body_succeeded_label():
    m = _make_metrics(attempts=[(0, None)], succeeded=True)
    body = alert_body(m, "cmd")
    assert "SUCCEEDED" in body


def test_alert_body_includes_delays():
    m = _make_metrics(attempts=[(1, 2.5), (0, None)], succeeded=True)
    body = alert_body(m, "cmd")
    assert "2.5" in body
