"""Label and tagging support for retry runs.

Allows users to attach a named label and arbitrary key=value tags to a
retry invocation so that log output, audit entries, and alert bodies can
be correlated across distributed systems or CI pipelines.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class LabelConfig:
    """Configuration for run labelling."""

    name: Optional[str] = None
    tags: Dict[str, str] = field(default_factory=dict)

    # ------------------------------------------------------------------ #
    # Construction
    # ------------------------------------------------------------------ #

    @classmethod
    def from_dict(cls, data: dict) -> "LabelConfig":
        """Build a LabelConfig from a raw mapping (e.g. parsed TOML)."""
        raw_tags = data.get("tags", {})
        if not isinstance(raw_tags, dict):
            raise ValueError("label.tags must be a mapping of string keys to string values")
        tags = {str(k): str(v) for k, v in raw_tags.items()}
        return cls(
            name=data.get("name") or None,
            tags=tags,
        )


def format_label(cfg: LabelConfig) -> str:
    """Return a human-readable label string suitable for log lines.

    Examples
    --------
    >>> format_label(LabelConfig(name="deploy", tags={"env": "prod"}))
    'deploy [env=prod]'
    >>> format_label(LabelConfig())
    '(unlabelled)'
    """
    parts: list[str] = []
    if cfg.name:
        parts.append(cfg.name)
    if cfg.tags:
        tag_str = " ".join(f"{k}={v}" for k, v in sorted(cfg.tags.items()))
        parts.append(f"[{tag_str}]")
    return " ".join(parts) if parts else "(unlabelled)"


def label_to_dict(cfg: LabelConfig) -> dict:
    """Serialise a LabelConfig to a plain dict for audit / metrics output."""
    return {
        "name": cfg.name,
        "tags": dict(cfg.tags),
    }
