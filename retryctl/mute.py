"""mute.py — suppress output or alerts for a run based on configurable conditions."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class MuteConfig:
    enabled: bool = False
    exit_codes: List[int] = field(default_factory=list)
    patterns: List[str] = field(default_factory=list)
    suppress_alerts: bool = True
    suppress_output: bool = False
    _compiled: List[re.Pattern] = field(default_factory=list, init=False, repr=False)

    def __post_init__(self) -> None:
        self._compiled = [re.compile(p) for p in self.patterns]

    @classmethod
    def from_dict(cls, raw: object) -> "MuteConfig":
        if not isinstance(raw, dict):
            raise TypeError(f"mute config must be a dict, got {type(raw).__name__}")
        exit_codes = raw.get("exit_codes", [])
        if not isinstance(exit_codes, list):
            raise TypeError("mute.exit_codes must be a list")
        patterns = raw.get("patterns", [])
        if not isinstance(patterns, list):
            raise TypeError("mute.patterns must be a list")
        auto_enable = bool(exit_codes or patterns)
        enabled = bool(raw.get("enabled", auto_enable))
        return cls(
            enabled=enabled,
            exit_codes=[int(c) for c in exit_codes],
            patterns=[str(p) for p in patterns],
            suppress_alerts=bool(raw.get("suppress_alerts", True)),
            suppress_output=bool(raw.get("suppress_output", False)),
        )


def is_muted(
    cfg: MuteConfig,
    exit_code: int,
    output: str = "",
) -> bool:
    """Return True if this result should be muted based on exit code or output patterns."""
    if not cfg.enabled:
        return False
    if exit_code in cfg.exit_codes:
        return True
    for pattern in cfg._compiled:
        if pattern.search(output):
            return True
    return False


def mute_config_summary(cfg: MuteConfig) -> Optional[str]:
    if not cfg.enabled:
        return None
    parts = []
    if cfg.exit_codes:
        parts.append(f"exit_codes={cfg.exit_codes}")
    if cfg.patterns:
        parts.append(f"patterns={cfg.patterns}")
    flags = []
    if cfg.suppress_alerts:
        flags.append("suppress_alerts")
    if cfg.suppress_output:
        flags.append("suppress_output")
    if flags:
        parts.append(",".join(flags))
    return "mute(" + " ".join(parts) + ")"
