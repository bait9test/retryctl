"""Thin hook that wires audit logging into the finalize_run pipeline."""

from __future__ import annotations

import logging

from retryctl.audit import AuditConfig, build_audit_entry, write_audit_entry
from retryctl.metrics import RunMetrics

log = logging.getLogger(__name__)


def audit_on_finish(
    command: str,
    metrics: RunMetrics,
    cfg: AuditConfig,
) -> None:
    """Build and persist an audit entry for the completed run.

    Designed to be called from summary_hook.finalize_run or directly
    at the end of the CLI main loop.
    """
    if not cfg.enabled:
        log.debug("audit: disabled, skipping")
        return

    try:
        entry = build_audit_entry(command, metrics)
        write_audit_entry(entry, cfg)
        log.debug("audit: entry written to %s", cfg.audit_file)
    except Exception as exc:  # pragma: no cover
        log.warning("audit: unexpected error: %s", exc)
