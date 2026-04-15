"""Middleware helpers for the shimmer feature."""
from __future__ import annotations

from typing import Any

from retryctl.shimmer import ShimmerConfig, ShimmerTracker


def parse_shimmer(config: dict[str, Any]) -> ShimmerConfig:
    """Extract and parse the [shimmer] section from a full config dict."""
    raw = config.get("shimmer", {})
    if not isinstance(raw, dict):
        raise TypeError(f"[shimmer] must be a table, got {type(raw).__name__}")
    return ShimmerConfig.from_dict(raw)


def shimmer_config_to_dict(cfg: ShimmerConfig) -> dict[str, Any]:
    return {
        "enabled": cfg.enabled,
        "skip_rate": cfg.skip_rate,
        "seed": cfg.seed,
    }


def make_tracker(cfg: ShimmerConfig) -> ShimmerTracker:
    return ShimmerTracker(cfg)


def before_attempt(tracker: ShimmerTracker, attempt: int) -> None:
    """Call before each attempt; raises ShimmerSkipped if the attempt should be dropped."""
    tracker.check(attempt)


def describe_shimmer(cfg: ShimmerConfig) -> str:
    if not cfg.enabled:
        return "shimmer disabled"
    return f"shimmer enabled: skip_rate={cfg.skip_rate:.0%}" + (
        f", seed={cfg.seed}" if cfg.seed is not None else ""
    )
