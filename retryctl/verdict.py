"""verdict.py — classify a run outcome into a human-readable verdict string.

The verdict summarises *why* a run ended: succeeded, exhausted retries,
aborted by a fatal exit code, timed out, blocked by a gate, etc.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class VerdictCode(str, Enum):
    SUCCESS = "success"
    EXHAUSTED = "exhausted"        # ran out of retries
    ABORTED = "aborted"            # fatal exit code / abort condition
    TIMED_OUT = "timed_out"        # deadline / timeout exceeded
    GATE_BLOCKED = "gate_blocked"  # a pre-attempt gate refused the run
    SUPPRESSED = "suppressed"      # failure suppressed by suppress config
    UNKNOWN = "unknown"


@dataclass
class Verdict:
    code: VerdictCode
    reason: str = ""
    exit_code: Optional[int] = None
    attempts: int = 0
    extra: dict = field(default_factory=dict)

    def __str__(self) -> str:  # pragma: no cover
        parts = [self.code.value]
        if self.reason:
            parts.append(self.reason)
        if self.exit_code is not None:
            parts.append(f"exit={self.exit_code}")
        return " | ".join(parts)

    def is_success(self) -> bool:
        return self.code is VerdictCode.SUCCESS


def classify(
    *,
    succeeded: bool,
    attempts: int,
    max_attempts: int,
    exit_code: Optional[int] = None,
    aborted: bool = False,
    timed_out: bool = False,
    gate_blocked: bool = False,
    suppressed: bool = False,
    reason: str = "",
) -> Verdict:
    """Return a :class:`Verdict` for the completed run."""
    if succeeded:
        code = VerdictCode.SUCCESS
        reason = reason or "command exited 0"
    elif gate_blocked:
        code = VerdictCode.GATE_BLOCKED
        reason = reason or "a gate blocked execution"
    elif timed_out:
        code = VerdictCode.TIMED_OUT
        reason = reason or "deadline exceeded"
    elif aborted:
        code = VerdictCode.ABORTED
        reason = reason or "fatal exit code or abort condition"
    elif suppressed:
        code = VerdictCode.SUPPRESSED
        reason = reason or "failure suppressed"
    elif attempts >= max_attempts:
        code = VerdictCode.EXHAUSTED
        reason = reason or f"exhausted {max_attempts} attempt(s)"
    else:
        code = VerdictCode.UNKNOWN
        reason = reason or "run ended for unknown reason"

    return Verdict(
        code=code,
        reason=reason,
        exit_code=exit_code,
        attempts=attempts,
    )
