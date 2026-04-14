"""Middleware helpers for the stamp feature."""
from __future__ import annotations

from typing import Any, Dict

from retryctl.stamp import StampConfig, StampTracker


def parse_stamp(raw_config: Dict[str, Any]) -> StampConfig:
    """Extract stamp config from the top-level config dict."""
    section = raw_config.get("stamp", {})
    if not isinstance(section, dict):
        raise TypeError(
            f"[stamp] config section must be a table, got {type(section).__name__}"
        )
    return StampConfig.from_dict(section)


def stamp_config_to_dict(cfg: StampConfig) -> Dict[str, Any]:
    """Serialise a StampConfig back to a plain dict (useful for audit/debug)."""
    return {
        "enabled": cfg.enabled,
        "include_monotonic": cfg.include_monotonic,
    }


def make_tracker(cfg: StampConfig) -> StampTracker:
    """Convenience factory so callers don't import StampTracker directly."""
    return StampTracker(config=cfg)


def before_attempt(tracker: StampTracker, attempt: int) -> None:
    """Call this before each attempt to record its timestamp."""
    tracker.record(attempt)


def describe_stamp(cfg: StampConfig) -> str:
    if not cfg.enabled:
        return "stamp: disabled"
    parts = ["stamp: enabled"]
    if cfg.include_monotonic:
        parts.append("monotonic=yes")
    return ", ".join(parts)
