"""Middleware that wraps run_with_retry with checkpoint resume/save logic."""

from __future__ import annotations

import logging
from typing import List

from retryctl.backoff import BackoffConfig, delay_sequence
from retryctl.checkpoint import CheckpointConfig
from retryctl.checkpoint_context import (
    finish_checkpoint,
    resume_attempt,
    update_checkpoint,
)
from retryctl.runner import RetryResult, run_with_retry

log = logging.getLogger(__name__)


def run_with_checkpoint(
    command: List[str],
    max_attempts: int,
    backoff_cfg: BackoffConfig,
    checkpoint_cfg: CheckpointConfig,
    *,
    shell: bool = False,
) -> RetryResult:
    """Run *command* with retry, resuming from a saved checkpoint if one exists.

    On each failed attempt the checkpoint is updated so that a subsequent
    invocation of retryctl can skip already-exhausted attempts.  On success
    or final failure the checkpoint is cleared.
    """
    cmd_key = " ".join(command)
    start_attempt = resume_attempt(checkpoint_cfg, cmd_key)

    if start_attempt >= max_attempts:
        log.warning(
            "checkpoint: start_attempt=%d >= max_attempts=%d, resetting",
            start_attempt,
            max_attempts,
        )
        start_attempt = 0

    remaining = max_attempts - start_attempt
    log.debug("checkpoint: running %d remaining attempt(s)", remaining)

    result = run_with_retry(
        command,
        max_attempts=remaining,
        backoff_cfg=backoff_cfg,
        shell=shell,
        attempt_callback=lambda attempt, exit_code: update_checkpoint(
            checkpoint_cfg, cmd_key, start_attempt + attempt, exit_code
        ),
    )

    finish_checkpoint(checkpoint_cfg, cmd_key)
    return result
