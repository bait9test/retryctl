"""Tag-based filtering: allow or block retry runs by tag membership."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Collection, List, Optional


@dataclass
class TagFilterConfig:
    """Configuration for tag-based allow/block filtering."""

    require_any: List[str] = field(default_factory=list)
    """Run only if the label carries at least one of these tags."""

    block: List[str] = field(default_factory=list)
    """Refuse to run if the label carries any of these tags."""

    @staticmethod
    def from_dict(data: dict) -> "TagFilterConfig":
        require_any = [str(t) for t in data.get("require_any", [])]
        block = [str(t) for t in data.get("block", [])]
        return TagFilterConfig(require_any=require_any, block=block)


def is_blocked(tags: Collection[str], cfg: TagFilterConfig) -> bool:
    """Return True when *tags* contain a blocked tag."""
    return bool(set(tags) & set(cfg.block))


def meets_requirements(tags: Collection[str], cfg: TagFilterConfig) -> bool:
    """Return True when *tags* satisfy the require_any constraint (or none set)."""
    if not cfg.require_any:
        return True
    return bool(set(tags) & set(cfg.require_any))


def check_tag_gate(
    tags: Collection[str],
    cfg: TagFilterConfig,
) -> Optional[str]:
    """Return a human-readable rejection reason, or None if the run is allowed."""
    if is_blocked(tags, cfg):
        blocked = sorted(set(tags) & set(cfg.block))
        return f"run blocked by tag(s): {', '.join(blocked)}"
    if not meets_requirements(tags, cfg):
        return f"run requires one of {cfg.require_any!r}, got {sorted(tags)!r}"
    return None
