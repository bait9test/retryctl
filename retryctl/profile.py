"""Named retry profiles — load and resolve a named config profile."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class Profile:
    """A named collection of retry settings that can be referenced by name."""

    name: str
    description: str = ""
    settings: Dict[str, Any] = field(default_factory=dict)


def from_dict(name: str, data: Dict[str, Any]) -> Profile:
    """Build a Profile from a raw dict (e.g. from TOML)."""
    if not isinstance(data, dict):
        raise TypeError(f"Profile '{name}' must be a table, got {type(data).__name__}")
    return Profile(
        name=name,
        description=str(data.get("description", "")),
        settings={k: v for k, v in data.items() if k != "description"},
    )


def load_profiles(raw: Dict[str, Any]) -> Dict[str, Profile]:
    """Parse a [profiles] TOML section into a dict of Profile objects."""
    profiles: Dict[str, Profile] = {}
    for name, body in raw.items():
        profiles[name] = from_dict(name, body)
    return profiles


def resolve_profile(
    profiles: Dict[str, Profile],
    name: Optional[str],
) -> Optional[Profile]:
    """Return the named profile, or None if name is None.

    Raises KeyError with a helpful message when the name is not found.
    """
    if name is None:
        return None
    if name not in profiles:
        available = ", ".join(sorted(profiles)) or "(none)"
        raise KeyError(
            f"Profile '{name}' not found. Available profiles: {available}"
        )
    return profiles[name]


def merge_profile(
    base: Dict[str, Any],
    profile: Optional[Profile],
) -> Dict[str, Any]:
    """Shallow-merge profile settings into *base*, profile values win.

    Returns a new dict; *base* is not mutated.
    """
    if profile is None:
        return dict(base)
    merged = dict(base)
    merged.update(profile.settings)
    return merged
