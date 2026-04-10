"""Redaction support for sensitive values in logs, alerts, and audit output."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class RedactConfig:
    """Configuration for redacting sensitive patterns from output."""

    enabled: bool = True
    patterns: List[str] = field(default_factory=list)
    placeholder: str = "***"

    @classmethod
    def from_dict(cls, data: dict) -> "RedactConfig":
        return cls(
            enabled=bool(data.get("enabled", True)),
            patterns=list(data.get("patterns", [])),
            placeholder=str(data.get("placeholder", "***")),
        )


def _compile_patterns(patterns: List[str]) -> List[re.Pattern]:
    """Compile a list of regex pattern strings, skipping invalid ones."""
    compiled = []
    for p in patterns:
        try:
            compiled.append(re.compile(p))
        except re.error:
            pass
    return compiled


def redact(text: str, cfg: RedactConfig) -> str:
    """Return *text* with all configured patterns replaced by the placeholder.

    If redaction is disabled or there are no patterns, the original text is
    returned unchanged.
    """
    if not cfg.enabled or not cfg.patterns:
        return text

    compiled = _compile_patterns(cfg.patterns)
    result = text
    for pattern in compiled:
        result = pattern.sub(cfg.placeholder, result)
    return result


def redact_env(env: dict, cfg: RedactConfig) -> dict:
    """Return a copy of *env* with values redacted according to *cfg*."""
    return {k: redact(v, cfg) for k, v in env.items()}
