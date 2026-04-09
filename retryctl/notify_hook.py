"""Integrates NotifyConfig with the run lifecycle."""
from __future__ import annotations

import logging
from typing import Optional

from retryctl.metrics import RunMetrics
from retryctl.notify import NotifyConfig, send_notification

log = logging.getLogger(__name__)


def _build_message(metrics: RunMetrics, command: str) -> str:
    """Build a human-readable notification body."""
    status = "succeeded" if metrics.succeeded else "failed"
    attempts = metrics.total_attempts
    noun = "attempt" if attempts == 1 else "attempts"
    short_cmd = command[:60] + "..." if len(command) > 60 else command
    return f"`{short_cmd}` {status} after {attempts} {noun}."


def notify_on_finish(
    cfg: Optional[NotifyConfig],
    metrics: RunMetrics,
    command: str,
) -> None:
    """Called at the end of a run to fire a desktop notification if configured."""
    if cfg is None:
        return
    message = _build_message(metrics, command)
    sent = send_notification(cfg, message, success=bool(metrics.succeeded))
    if sent:
        log.debug("notify_hook: notification dispatched")
    else:
        log.debug("notify_hook: notification skipped or unavailable")
