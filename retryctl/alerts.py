"""Alerting module for retryctl — sends notifications when commands fail."""

import smtplib
import logging
from dataclasses import dataclass, field
from email.mime.text import MIMEText
from enum import Enum
from typing import Optional, List

logger = logging.getLogger(__name__)


class AlertChannel(str, Enum):
    LOG = "log"
    EMAIL = "email"
    WEBHOOK = "webhook"


@dataclass
class AlertConfig:
    channels: List[AlertChannel] = field(default_factory=lambda: [AlertChannel.LOG])
    email_to: Optional[str] = None
    email_from: Optional[str] = None
    smtp_host: str = "localhost"
    smtp_port: int = 25
    webhook_url: Optional[str] = None
    min_attempts_before_alert: int = 1


@dataclass
class AlertContext:
    command: str
    attempt: int
    max_attempts: int
    exit_code: Optional[int]
    stderr: str = ""
    final_failure: bool = False


def send_log_alert(ctx: AlertContext) -> None:
    level = logging.ERROR if ctx.final_failure else logging.WARNING
    msg = (
        f"[retryctl] Command failed: '{ctx.command}' | "
        f"attempt {ctx.attempt}/{ctx.max_attempts} | exit_code={ctx.exit_code}"
    )
    if ctx.final_failure:
        msg += " | FINAL FAILURE"
    logger.log(level, msg)


def send_email_alert(ctx: AlertContext, cfg: AlertConfig) -> None:
    if not cfg.email_to or not cfg.email_from:
        logger.warning("Email alert configured but email_to/email_from not set")
        return
    subject = f"[retryctl] Command failed: {ctx.command[:60]}"
    body = (
        f"Command: {ctx.command}\n"
        f"Attempt: {ctx.attempt}/{ctx.max_attempts}\n"
        f"Exit code: {ctx.exit_code}\n"
        f"Final failure: {ctx.final_failure}\n"
        f"Stderr:\n{ctx.stderr}"
    )
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = cfg.email_from
    msg["To"] = cfg.email_to
    try:
        with smtplib.SMTP(cfg.smtp_host, cfg.smtp_port) as server:
            server.sendmail(cfg.email_from, [cfg.email_to], msg.as_string())
        logger.debug("Email alert sent to %s", cfg.email_to)
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to send email alert: %s", exc)


def send_webhook_alert(ctx: AlertContext, cfg: AlertConfig) -> None:
    import urllib.request
    import json

    if not cfg.webhook_url:
        logger.warning("Webhook alert configured but webhook_url not set")
        return
    payload = json.dumps({
        "command": ctx.command,
        "attempt": ctx.attempt,
        "max_attempts": ctx.max_attempts,
        "exit_code": ctx.exit_code,
        "final_failure": ctx.final_failure,
        "stderr": ctx.stderr,
    }).encode()
    req = urllib.request.Request(
        cfg.webhook_url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            logger.debug("Webhook alert sent, status=%s", resp.status)
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to send webhook alert: %s", exc)


def dispatch_alerts(ctx: AlertContext, cfg: AlertConfig) -> None:
    """Dispatch alerts to all configured channels if attempt threshold is met."""
    if ctx.attempt < cfg.min_attempts_before_alert:
        return
    for channel in cfg.channels:
        if channel == AlertChannel.LOG:
            send_log_alert(ctx)
        elif channel == AlertChannel.EMAIL:
            send_email_alert(ctx, cfg)
        elif channel == AlertChannel.WEBHOOK:
            send_webhook_alert(ctx, cfg)
