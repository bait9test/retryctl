"""Suppress specific exit codes or output patterns from being treated as failures."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional, Pattern


@dataclass
class SuppressConfig:
    enabled: bool = False
    exit_codes: List[int] = field(default_factory=list)
    stdout_patterns: List[str] = field(default_factory=list)
    stderr_patterns: List[str] = field(default_factory=list)

    _stdout_re: List[Pattern] = field(default_factory=list, init=False, repr=False)
    _stderr_re: List[Pattern] = field(default_factory=list, init=False, repr=False)

    def __post_init__(self) -> None:
        self._stdout_re = _compile(self.stdout_patterns)
        self._stderr_re = _compile(self.stderr_patterns)


def from_dict(data: dict) -> SuppressConfig:
    if not isinstance(data, dict):
        raise TypeError(f"suppress config must be a dict, got {type(data).__name__}")
    raw_codes = data.get("exit_codes", [])
    if not isinstance(raw_codes, list):
        raise TypeError("suppress.exit_codes must be a list")
    codes = [int(c) for c in raw_codes]
    stdout_p = list(data.get("stdout_patterns", []))
    stderr_p = list(data.get("stderr_patterns", []))
    enabled = bool(
        data.get("enabled", bool(codes or stdout_p or stderr_p))
    )
    return SuppressConfig(
        enabled=enabled,
        exit_codes=codes,
        stdout_patterns=stdout_p,
        stderr_patterns=stderr_p,
    )


def _compile(patterns: List[str]) -> List[Pattern]:
    return [re.compile(p) for p in patterns]


def is_suppressed(
    cfg: SuppressConfig,
    exit_code: int,
    stdout: Optional[str] = None,
    stderr: Optional[str] = None,
) -> bool:
    """Return True if the result should be treated as a non-failure."""
    if not cfg.enabled:
        return False
    if exit_code in cfg.exit_codes:
        return True
    if stdout and any(rx.search(stdout) for rx in cfg._stdout_re):
        return True
    if stderr and any(rx.search(stderr) for rx in cfg._stderr_re):
        return True
    return False


def suppress_config_to_dict(cfg: SuppressConfig) -> dict:
    return {
        "enabled": cfg.enabled,
        "exit_codes": list(cfg.exit_codes),
        "stdout_patterns": list(cfg.stdout_patterns),
        "stderr_patterns": list(cfg.stderr_patterns),
    }
