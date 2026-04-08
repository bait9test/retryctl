"""Integrate reporter with hooks and alerts at run completion."""

from __future__ import annotations

import logging
from typing import Optional

from retryctl.metrics import RunMetrics
from retryctl.reporter import log_summary, alert_body
from retryctl.alerts import AlertConfig, AlertContext, dispatch_alert
from retryctl.hooks import HookConfig, run_post_hooks

logger = logging.getLogger(__name__)


def finalize_run(
    *,
    metrics: RunMetrics,
    command: str,
    alert_config: Optional[AlertConfig] = None,
    hook_config: Optional[HookConfig] = None,
    exit_code: int = 0,
) -> None:
    """Log summary, fire post-hooks, and dispatch alerts after a run.

    This is the single call-site that wires together the reporter,
    hooks, and alerting subsystems so the CLI and tests only need one
    entry point.
    """
    log_summary(metrics, command)

    if hook_config is not None:
        try:
            run_post_hooks(hook_config, exit_code=exit_code, succeeded=metrics.succeeded)
        except Exception:
            logger.exception("post-hook dispatch raised an unexpected error")

    if alert_config is not None:
        body = alert_body(metrics, command)
        ctx = AlertContext(
            attempt=metrics.total_attempts,
            max_attempts=metrics.total_attempts,
            exit_code=exit_code,
            command=command,
            succeeded=metrics.succeeded,
            extra={"body": body},
        )
        try:
            dispatch_alert(alert_config, ctx)
        except Exception:
            logger.exception("alert dispatch raised an unexpected error")
