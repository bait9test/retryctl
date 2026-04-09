"""Environment variable injection for retried commands."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class EnvConfig:
    """Configuration for environment variable injection."""

    # Extra vars to inject into every attempt
    extra: Dict[str, str] = field(default_factory=dict)
    # If True, pass the current process environment through
    inherit: bool = True
    # Vars to remove even if inherited
    unset: list = field(default_factory=list)


def from_dict(data: dict) -> EnvConfig:
    """Build an EnvConfig from a raw config dict (e.g. parsed TOML)."""
    return EnvConfig(
        extra=dict(data.get("extra", {})),
        inherit=bool(data.get("inherit", True)),
        unset=list(data.get("unset", [])),
    )


def build_env(cfg: EnvConfig, attempt: int, max_attempts: int) -> Dict[str, str]:
    """Return the environment mapping to use when launching a command.

    Always injects ``RETRYCTL_ATTEMPT`` (1-based) and
    ``RETRYCTL_MAX_ATTEMPTS`` so scripts can inspect retry context.
    """
    base: Dict[str, str] = dict(os.environ) if cfg.inherit else {}

    for key in cfg.unset:
        base.pop(key, None)

    base.update(cfg.extra)

    # Built-in retry context vars (always present, may be overridden by extra)
    base.setdefault("RETRYCTL_ATTEMPT", str(attempt))
    base.setdefault("RETRYCTL_MAX_ATTEMPTS", str(max_attempts))

    return base


def merge_env_override(cfg: EnvConfig, overrides: Optional[Dict[str, str]]) -> EnvConfig:
    """Return a new EnvConfig with *overrides* merged on top of cfg.extra."""
    if not overrides:
        return cfg
    merged = dict(cfg.extra)
    merged.update(overrides)
    return EnvConfig(extra=merged, inherit=cfg.inherit, unset=list(cfg.unset))
