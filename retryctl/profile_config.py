"""Integration between RetryCtlConfig and the profile system.

Provides a single entry-point used by cli.py / config.py to resolve
a profile and return a fully-merged raw config dict.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from retryctl.profile_middleware import apply_profile


def resolve_config_with_profile(
    raw: Dict[str, Any],
    profile_override: Optional[str] = None,
) -> Dict[str, Any]:
    """Given the raw parsed TOML dict and an optional CLI profile override,
    return a merged config dict ready for ``load_config`` consumption.

    Priority (highest → lowest):
      1. *profile_override* from CLI flag ``--profile``
      2. ``profile = "name"`` key inside the TOML file
      3. No profile — raw config is used as-is
    """
    return apply_profile(raw, profile_name=profile_override)


def list_profile_names(raw: Dict[str, Any]) -> list[str]:
    """Return sorted list of profile names defined in *raw* config."""
    return sorted(raw.get("profiles", {}).keys())
