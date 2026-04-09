"""High-level helpers that wire checkpoint load/save into the retry loop."""

from __future__ import annotations

import logging
from typing import Optional

from retryctl.checkpoint import (
    CheckpointConfig,
    CheckpointData,
    clear_checkpoint,
    load_checkpoint,
    save_checkpoint,
)

log = logging.getLogger(__name__)


def resume_attempt(cfg: CheckpointConfig, command: str) -> int:
    """Return the attempt number to start from (0-based). Logs if resuming."""
    data = load_checkpoint(cfg, command)
    if data is None:
        return 0
    log.info(
        "checkpoint: resuming command %r from attempt %d (last exit code: %s)",
        command,
        data.attempt,
        data.last_exit_code,
    )
    return data.attempt


def update_checkpoint(
    cfg: CheckpointConfig,
    command: str,
    attempt: int,
    exit_code: Optional[int],
) -> None:
    """Persist current progress so a future run can resume."""
    data = CheckpointData(
        command=command,
        attempt=attempt,
        last_exit_code=exit_code,
    )
    save_checkpoint(cfg, data)
    log.debug("checkpoint: saved attempt=%d exit_code=%s", attempt, exit_code)


def finish_checkpoint(cfg: CheckpointConfig, command: str) -> None:
    """Remove the checkpoint file once the run is complete (success or exhausted)."""
    clear_checkpoint(cfg, command)
    log.debug("checkpoint: cleared for command %r", command)
