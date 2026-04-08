"""Aggregate run results and emit a human-readable summary report."""

from __future__ import annotations

import logging
from typing import Optional

from retryctl.metrics import RunMetrics
from retryctl.output import CapturedOutput, OutputConfig, format_output, truncate_for_alert

log = logging.getLogger(__name__)

_STATUS_OK = "\u2705"   # ✅
_STATUS_FAIL = "\u274c"  # ❌
_DIVIDER = "-" * 60


def _duration_str(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.2f}s"
    m, s = divmod(int(seconds), 60)
    return f"{m}m {s}s"


def build_summary(
    metrics: RunMetrics,
    command: str,
    captured: Optional[CapturedOutput] = None,
    output_config: Optional[OutputConfig] = None,
) -> str:
    """Return a multi-line summary string for a completed run."""
    status_icon = _STATUS_OK if metrics.succeeded else _STATUS_FAIL
    status_word = "SUCCEEDED" if metrics.succeeded else "FAILED"

    duration = (
        (metrics.finished_at - metrics.started_at).total_seconds()
        if metrics.finished_at and metrics.started_at
        else 0.0
    )

    lines = [
        _DIVIDER,
        f"{status_icon}  retryctl run {status_word}",
        f"   command   : {command}",
        f"   attempts  : {metrics.total_attempts}",
        f"   duration  : {_duration_str(duration)}",
    ]

    if metrics.attempts:
        last = metrics.attempts[-1]
        lines.append(f"   exit code : {last.exit_code}")
        if last.error:
            lines.append(f"   error     : {last.error}")

    if metrics.total_attempts > 1:
        delays = [a.delay_before for a in metrics.attempts if a.delay_before > 0]
        if delays:
            total_wait = sum(delays)
            lines.append(f"   total wait: {_duration_str(total_wait)}")

    if captured is not None and output_config is not None:
        formatted = format_output(captured, output_config, succeeded=metrics.succeeded)
        if formatted:
            lines.append("")
            lines.append("   --- output ---")
            for ol in formatted.splitlines():
                lines.append(f"   {ol}")

    lines.append(_DIVIDER)
    return "\n".join(lines)


def log_summary(
    metrics: RunMetrics,
    command: str,
    captured: Optional[CapturedOutput] = None,
    output_config: Optional[OutputConfig] = None,
) -> None:
    """Write the summary to the logger at the appropriate level."""
    summary = build_summary(metrics, command, captured, output_config)
    if metrics.succeeded:
        log.info(summary)
    else:
        log.error(summary)


def alert_body(
    metrics: RunMetrics,
    command: str,
    captured: Optional[CapturedOutput] = None,
    max_output_chars: int = 500,
) -> str:
    """Return a compact string suitable for embedding in an alert payload."""
    status = "SUCCEEDED" if metrics.succeeded else "FAILED"
    last_code = metrics.attempts[-1].exit_code if metrics.attempts else "?"
    body = (
        f"retryctl run {status}\n"
        f"command: {command}\n"
        f"attempts: {metrics.total_attempts}, exit_code: {last_code}\n"
    )
    if captured:
        combined = ""
        if captured.stderr:
            combined = captured.stderr
        elif captured.stdout:
            combined = captured.stdout
        if combined:
            body += "\noutput:\n" + truncate_for_alert(combined, max_output_chars)
    return body
