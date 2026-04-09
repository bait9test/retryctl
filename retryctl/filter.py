"""Exit-code and stderr pattern filtering to decide whether a failure is retryable."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class FilterConfig:
    """Rules that determine whether a failed attempt should be retried."""

    # If non-empty, only these exit codes are considered retryable.
    # An empty list means *all* non-zero exit codes are retryable.
    retryable_exit_codes: List[int] = field(default_factory=list)

    # If non-empty, at least one pattern must match stderr for the attempt
    # to be considered retryable.  Empty means stderr is not checked.
    retryable_stderr_patterns: List[str] = field(default_factory=list)

    # Exit codes that should immediately abort retrying (never retried).
    fatal_exit_codes: List[int] = field(default_factory=list)


def is_retryable(
    exit_code: int,
    stderr: str,
    cfg: FilterConfig,
) -> bool:
    """Return True when the attempt should be retried according to *cfg*.

    Rules (evaluated in order):
    1. Exit code 0 is never retried.
    2. Fatal exit codes are never retried.
    3. If retryable_exit_codes is set, the exit code must be in the list.
    4. If retryable_stderr_patterns is set, at least one must match stderr.
    """
    if exit_code == 0:
        return False

    if exit_code in cfg.fatal_exit_codes:
        return False

    if cfg.retryable_exit_codes and exit_code not in cfg.retryable_exit_codes:
        return False

    if cfg.retryable_stderr_patterns:
        return any(
            re.search(pattern, stderr) for pattern in cfg.retryable_stderr_patterns
        )

    return True


def should_abort(
    exit_code: int,
    cfg: FilterConfig,
) -> bool:
    """Return True when the exit code is in the fatal list and retrying must stop."""
    return exit_code in cfg.fatal_exit_codes
