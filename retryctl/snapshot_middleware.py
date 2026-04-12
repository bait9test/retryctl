"""Snapshot middleware helpers — parse config and integrate with the retry loop."""
from __future__ import annotations

import logging
from typing import Optional

from retryctl.snapshot import (
    SnapshotConfig,
    SnapshotEntry,
    compare_snapshots,
    save_snapshots,
    take_snapshot,
)

log = logging.getLogger(__name__)


def parse_snapshot(raw: dict) -> SnapshotConfig:
    section = raw.get("snapshot", {})
    if not isinstance(section, dict):
        raise TypeError("[snapshot] must be a table")
    return SnapshotConfig.from_dict(section)


def snapshot_config_to_dict(cfg: SnapshotConfig) -> dict:
    return {
        "enabled": cfg.enabled,
        "path": cfg.path,
        "compare_stdout": cfg.compare_stdout,
        "compare_stderr": cfg.compare_stderr,
        "fail_on_change": cfg.fail_on_change,
    }


def on_attempt_complete(
    cfg: SnapshotConfig,
    key: str,
    attempt: int,
    stdout: Optional[str],
    stderr: Optional[str],
    history: list[SnapshotEntry],
) -> tuple[bool, list[SnapshotEntry]]:
    """Record a snapshot for this attempt; return (changed, updated_history)."""
    if not cfg.enabled:
        return False, history

    entry = take_snapshot(cfg, attempt, stdout, stderr)
    changed = False
    if history:
        changed = compare_snapshots(history[-1], entry)
        entry.changed = changed
        if changed:
            log.info("snapshot: output changed on attempt %d for key '%s'", attempt, key)
        else:
            log.debug("snapshot: output unchanged on attempt %d for key '%s'", attempt, key)

    history = history + [entry]
    save_snapshots(cfg, key, history)
    return changed, history


def describe_snapshot(cfg: SnapshotConfig) -> str:
    if not cfg.enabled:
        return "snapshot: disabled"
    parts = []
    if cfg.compare_stdout:
        parts.append("stdout")
    if cfg.compare_stderr:
        parts.append("stderr")
    tracked = ", ".join(parts) or "nothing"
    action = "fail" if cfg.fail_on_change else "log"
    return f"snapshot: tracking {tracked}, action on change={action}, dir={cfg.path}"
