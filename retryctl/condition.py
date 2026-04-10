"""Condition evaluation for retry decisions based on stdout/stderr patterns."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class ConditionConfig:
    """Configuration for retry conditions based on output patterns."""

    retry_on_stdout: List[str] = field(default_factory=list)
    retry_on_stderr: List[str] = field(default_factory=list)
    abort_on_stdout: List[str] = field(default_factory=list)
    abort_on_stderr: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self._retry_stdout_re = _compile(self.retry_on_stdout)
        self._retry_stderr_re = _compile(self.retry_on_stderr)
        self._abort_stdout_re = _compile(self.abort_on_stdout)
        self._abort_stderr_re = _compile(self.abort_on_stderr)


def from_dict(data: dict) -> ConditionConfig:
    """Build a ConditionConfig from a raw mapping (e.g. parsed TOML)."""
    return ConditionConfig(
        retry_on_stdout=list(data.get("retry_on_stdout", [])),
        retry_on_stderr=list(data.get("retry_on_stderr", [])),
        abort_on_stdout=list(data.get("abort_on_stdout", [])),
        abort_on_stderr=list(data.get("abort_on_stderr", [])),
    )


def _compile(patterns: List[str]) -> List[re.Pattern]:
    return [re.compile(p) for p in patterns]


def _any_match(patterns: List[re.Pattern], text: Optional[str]) -> bool:
    if not text or not patterns:
        return False
    return any(p.search(text) for p in patterns)


def should_retry_on_output(
    cfg: ConditionConfig,
    stdout: Optional[str],
    stderr: Optional[str],
) -> bool:
    """Return True if any retry_on pattern matches stdout or stderr."""
    if not cfg.retry_on_stdout and not cfg.retry_on_stderr:
        return False
    return _any_match(cfg._retry_stdout_re, stdout) or _any_match(
        cfg._retry_stderr_re, stderr
    )


def should_abort_on_output(
    cfg: ConditionConfig,
    stdout: Optional[str],
    stderr: Optional[str],
) -> bool:
    """Return True if any abort_on pattern matches stdout or stderr."""
    if not cfg.abort_on_stdout and not cfg.abort_on_stderr:
        return False
    return _any_match(cfg._abort_stdout_re, stdout) or _any_match(
        cfg._abort_stderr_re, stderr
    )
