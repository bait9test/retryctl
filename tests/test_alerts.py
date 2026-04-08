"""Tests for the alerting module."""

import logging
from unittest.mock import MagicMock, patch

import pytest

from retryctl.alerts import (
    AlertChannel,
    AlertConfig,
    AlertContext,
    dispatch_alerts,
    send_log_alert,
    send_email_alert,
    send_webhook_alert,
)


@pytest.fixture
def ctx():
    return AlertContext(
        command="echo hello",
        attempt=2,
        max_attempts=3,
        exit_code=1,
        stderr="something went wrong",
        final_failure=False,
    )


def test_send_log_alert_warning(ctx, caplog):
    with caplog.at_level(logging.WARNING, logger="retryctl.alerts"):
        send_log_alert(ctx)
    assert "echo hello" in caplog.text
    assert "2/3" in caplog.text


def test_send_log_alert_error_on_final(ctx, caplog):
    ctx.final_failure = True
    with caplog.at_level(logging.ERROR, logger="retryctl.alerts"):
        send_log_alert(ctx)
    assert "FINAL FAILURE" in caplog.text


def test_dispatch_below_threshold_does_nothing(ctx, caplog):
    cfg = AlertConfig(channels=[AlertChannel.LOG], min_attempts_before_alert=5)
    ctx.attempt = 2
    with caplog.at_level(logging.WARNING):
        dispatch_alerts(ctx, cfg)
    assert caplog.text == ""


def test_dispatch_at_threshold_logs(ctx, caplog):
    cfg = AlertConfig(channels=[AlertChannel.LOG], min_attempts_before_alert=2)
    with caplog.at_level(logging.WARNING, logger="retryctl.alerts"):
        dispatch_alerts(ctx, cfg)
    assert "echo hello" in caplog.text


def test_send_email_alert_missing_config_warns(ctx, caplog):
    cfg = AlertConfig(channels=[AlertChannel.EMAIL])
    with caplog.at_level(logging.WARNING, logger="retryctl.alerts"):
        send_email_alert(ctx, cfg)
    assert "email_to" in caplog.text


def test_send_email_alert_sends(ctx):
    cfg = AlertConfig(
        channels=[AlertChannel.EMAIL],
        email_to="ops@example.com",
        email_from="retryctl@example.com",
        smtp_host="localhost",
        smtp_port=25,
    )
    with patch("smtplib.SMTP") as mock_smtp:
        instance = mock_smtp.return_value.__enter__.return_value
        send_email_alert(ctx, cfg)
        instance.sendmail.assert_called_once()


def test_send_webhook_alert_missing_url_warns(ctx, caplog):
    cfg = AlertConfig(channels=[AlertChannel.WEBHOOK])
    with caplog.at_level(logging.WARNING, logger="retryctl.alerts"):
        send_webhook_alert(ctx, cfg)
    assert "webhook_url" in caplog.text


def test_send_webhook_alert_posts(ctx):
    cfg = AlertConfig(
        channels=[AlertChannel.WEBHOOK],
        webhook_url="http://hooks.example.com/notify",
    )
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.__enter__ = lambda s: mock_response
    mock_response.__exit__ = MagicMock(return_value=False)
    with patch("urllib.request.urlopen", return_value=mock_response):
        send_webhook_alert(ctx, cfg)  # should not raise


def test_dispatch_multiple_channels(ctx, caplog):
    cfg = AlertConfig(
        channels=[AlertChannel.LOG, AlertChannel.WEBHOOK],
        webhook_url="http://hooks.example.com/notify",
        min_attempts_before_alert=1,
    )
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.__enter__ = lambda s: mock_response
    mock_response.__exit__ = MagicMock(return_value=False)
    with patch("urllib.request.urlopen", return_value=mock_response):
        with caplog.at_level(logging.WARNING, logger="retryctl.alerts"):
            dispatch_alerts(ctx, cfg)
    assert "echo hello" in caplog.text
