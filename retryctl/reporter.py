"""Summary reporting for retry runs."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Optional

from retryctl.metrics import RunMetrics

logger = logging.getLogger(__name__)


def _duration_str(seconds: float) -> str:
    """Format a duration in seconds as a human-readable string."""
    td = timedelta(seconds=seconds)
    total = int(td.total_seconds())
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    parts = []
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    parts.append(f"{secs}s")
    return " ".join(parts)


def build_summary(metrics: RunMetrics, command: str) -> dict:
    """Build a structured summary dict from run metrics."""
    duration = (
        (metrics.ended_at - metrics.started_at)
        if metrics.ended_at and metrics.started_at
        else 0.0
    )
    failed_attempts = [
        a for a in metrics.attempts if not a.succeeded
    ]
    return {
        "command": command,
        "succeeded": metrics.succeeded,
        "total_attempts": metrics.total_attempts,
        "failed_attempts": len(failed_attempts),
        "duration_seconds": round(duration, 3),
        "duration_human": _duration_str(duration),
        "exit_codes": [a.exit_code for a in metrics.attempts],
        "delays": [a.delay_before for a in metrics.attempts if a.delay_before],
    }


def log_summary(metrics: RunMetrics, command: str) -> None:
    """Log a human-readable summary of the retry run."""
    summary = build_summary(metrics, command)
    status = "succeeded" if summary["succeeded"] else "failed"
    logger.info(
        "retryctl run %s | command=%r attempts=%d duration=%s",
        status,
        summary["command"],
        summary["total_attempts"],
        summary["duration_human"],
    )
    if not summary["succeeded"]:
        logger.warning(
            "All %d attempt(s) failed. Exit codes: %s",
            summary["failed_attempts"],
            summary["exit_codes"],
        )


def alert_body(metrics: RunMetrics, command: str) -> str:
    """Produce a plain-text alert body suitable for email/webhook payloads."""
    summary = build_summary(metrics, command)
    lines = [
        f"retryctl alert: command {'SUCCEEDED' if summary['succeeded'] else 'FAILED'}",
        f"Command   : {summary['command']}",
        f"Attempts  : {summary['total_attempts']}",
        f"Duration  : {summary['duration_human']}",
        f"Exit codes: {summary['exit_codes']}",
    ]
    if summary["delays"]:
        lines.append(f"Delays (s): {summary['delays']}")
    return "\n".join(lines)
