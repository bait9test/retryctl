"""Tests for config loading and CLI argument parsing."""

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from retryctl.backoff import BackoffStrategy
from retryctl.alerts import AlertChannel
from retryctl.config import RetryCtlConfig, load_config, _parse_backoff, _parse_alerts
from retryctl.cli import build_parser, apply_cli_overrides, main


def test_load_config_defaults():
    cfg = load_config(path=Path("/nonexistent/path.toml"))
    assert cfg.max_attempts == 3
    assert cfg.backoff.strategy == BackoffStrategy.FIXED
    assert cfg.backoff.base_delay == 1.0
    assert AlertChannel.LOG in cfg.alerts.channels


def test_load_config_env_override():
    with patch.dict(os.environ, {"RETRYCTL_MAX_ATTEMPTS": "7"}):
        cfg = load_config(path=Path("/nonexistent/path.toml"))
    assert cfg.max_attempts == 7


def test_parse_backoff_exponential():
    raw = {"strategy": "exponential", "base_delay": "2.5", "jitter": True}
    bc = _parse_backoff(raw)
    assert bc.strategy == BackoffStrategy.EXPONENTIAL
    assert bc.base_delay == 2.5
    assert bc.jitter is True


def test_parse_alerts_webhook():
    raw = {
        "channels": ["webhook", "log"],
        "webhook_url": "http://example.com/hook",
        "min_attempts_before_alert": 2,
    }
    ac = _parse_alerts(raw)
    assert AlertChannel.WEBHOOK in ac.channels
    assert ac.webhook_url == "http://example.com/hook"
    assert ac.min_attempts_before_alert == 2


def test_cli_no_command_returns_2():
    rc = main([])
    assert rc == 2


def test_cli_overrides_applied():
    cfg = RetryCtlConfig()
    parser = build_parser()
    args = parser.parse_args(["-n", "5", "--strategy", "linear", "--jitter", "echo", "hi"])
    cfg = apply_cli_overrides(cfg, args)
    assert cfg.max_attempts == 5
    assert cfg.backoff.strategy == BackoffStrategy.LINEAR
    assert cfg.backoff.jitter is True


def test_cli_runs_successful_command():
    rc = main(["--", "true"])
    assert rc == 0


def test_cli_runs_failing_command():
    rc = main(["-n", "2", "--base-delay", "0", "--", "false"])
    assert rc != 0


def test_cli_alert_channel_override():
    cfg = RetryCtlConfig()
    parser = build_parser()
    args = parser.parse_args(["--alert", "log", "--alert", "webhook",
                              "--webhook-url", "http://x.com", "echo"])
    cfg = apply_cli_overrides(cfg, args)
    assert AlertChannel.WEBHOOK in cfg.alerts.channels
    assert cfg.alerts.webhook_url == "http://x.com"
