"""Middleware that resolves a CLI/config profile and merges it into the
active configuration before a run starts.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from retryctl.profile import Profile, load_profiles, merge_profile, resolve_profile


def apply_profile(
    raw_config: Dict[str, Any],
    profile_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Load profiles from *raw_config*, resolve *profile_name*, and return
    a merged config dict with the profile's settings applied.

    If no ``[profiles]`` section exists or *profile_name* is None the
    original config is returned unchanged (as a shallow copy).
    """
    profiles_raw: Dict[str, Any] = raw_config.get("profiles", {})
    profiles = load_profiles(profiles_raw)

    # Honour an inline ``profile = "name"`` key when no explicit override.
    effective_name = profile_name or raw_config.get("profile")

    profile: Optional[Profile] = resolve_profile(profiles, effective_name)

    # Build a working copy without the profiles table itself.
    base = {k: v for k, v in raw_config.items() if k != "profiles"}
    return merge_profile(base, profile)


def describe_profiles(raw_config: Dict[str, Any]) -> str:
    """Return a human-readable listing of all defined profiles."""
    profiles_raw: Dict[str, Any] = raw_config.get("profiles", {})
    if not profiles_raw:
        return "No profiles defined."

    profiles = load_profiles(profiles_raw)
    lines = []
    for name in sorted(profiles):
        p = profiles[name]
        desc = f" — {p.description}" if p.description else ""
        keys = ", ".join(sorted(p.settings)) or "(empty)"
        lines.append(f"  {name}{desc}  [{keys}]")
    return "Profiles:\n" + "\n".join(lines)
