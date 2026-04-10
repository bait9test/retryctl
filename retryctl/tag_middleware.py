"""Middleware helpers for integrating tag filtering into the retry pipeline."""
from __future__ import annotations

import logging
from typing import Dict, List, Optional

from retryctl.tag import TagFilterConfig, check_tag_gate

log = logging.getLogger(__name__)


class TagGateBlocked(Exception):
    """Raised when a tag filter prevents the run from proceeding."""


def parse_tag_filter(config_dict: dict) -> TagFilterConfig:
    """Build a :class:`TagFilterConfig` from the ``[tag_filter]`` config section."""
    section = config_dict.get("tag_filter", {})
    if not isinstance(section, dict):
        raise TypeError(f"[tag_filter] must be a table, got {type(section).__name__}")
    return TagFilterConfig.from_dict(section)


def tag_filter_to_dict(cfg: TagFilterConfig) -> dict:
    """Serialise a :class:`TagFilterConfig` back to a plain dict."""
    return {
        "require_any": list(cfg.require_any),
        "block": list(cfg.block),
    }


def enforce_tag_gate(
    tags: List[str],
    cfg: TagFilterConfig,
    *,
    raise_on_block: bool = True,
) -> Optional[str]:
    """Check *tags* against *cfg*.

    Returns the rejection reason string when blocked/unmet, ``None`` when
    allowed.  If *raise_on_block* is True a :class:`TagGateBlocked` is raised
    instead of returning the reason string.
    """
    reason = check_tag_gate(tags, cfg)
    if reason is None:
        return None
    log.warning("tag gate: %s", reason)
    if raise_on_block:
        raise TagGateBlocked(reason)
    return reason
