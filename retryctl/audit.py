"""Audit log: persist a structured record of every retry run to a JSONL file."""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from retryctl.metrics import RunMetrics

log = logging.getLogger(__name__)

_DEFAULT_AUDIT_FILE = os.path.join(
    os.environ.get("XDG_STATE_HOME", os.path.expanduser("~/.local/state")),
    "retryctl",
    "audit.jsonl",
)


@dataclass
class AuditConfig:
    enabled: bool = False
    audit_file: str = _DEFAULT_AUDIT_FILE

    @classmethod
    def from_dict(cls, data: dict) -> "AuditConfig":
        return cls(
            enabled=bool(data.get("enabled", False)),
            audit_file=str(data.get("audit_file", _DEFAULT_AUDIT_FILE)),
        )


@dataclass
class AuditEntry:
    command: str
    succeeded: bool
    total_attempts: int
    elapsed_seconds: float
    finished_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    exit_code: Optional[int] = None

    def to_dict(self) -> dict:
        return asdict(self)


def build_audit_entry(command: str, metrics: RunMetrics) -> AuditEntry:
    elapsed = (
        (metrics.finished_at - metrics.started_at).total_seconds()
        if metrics.finished_at and metrics.started_at
        else 0.0
    )
    last_code: Optional[int] = None
    if metrics.attempts:
        last_code = metrics.attempts[-1].exit_code
    return AuditEntry(
        command=command,
        succeeded=metrics.succeeded,
        total_attempts=metrics.total_attempts,
        elapsed_seconds=round(elapsed, 3),
        exit_code=last_code,
    )


def write_audit_entry(entry: AuditEntry, cfg: AuditConfig) -> None:
    if not cfg.enabled:
        return
    path = Path(cfg.audit_file)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry.to_dict()) + "\n")
    except OSError as exc:
        log.warning("audit: could not write to %s: %s", cfg.audit_file, exc)
