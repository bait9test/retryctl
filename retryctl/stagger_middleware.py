"""Middleware helpers for the stagger feature."""
from __future__ import annotations

from typing import Any

from retryctl.stagger import StaggerConfig, apply_stagger, compute_stagger_delay


def parse_stagger(raw_config: dict[str, Any]) -> StaggerConfig:
    """Extract and parse the [stagger] section from a raw config dict."""
    section = raw_config.get("stagger", {})
    if not isinstance(section, dict):
        raise TypeError("[stagger] config section must be a mapping")
    return StaggerConfig.from_dict(section)


def stagger_config_to_dict(cfg: StaggerConfig) -> dict[str, Any]:
    """Serialise a StaggerConfig back to a plain dict (for audit / replay)."""
    return {
        "enabled": cfg.enabled,
        "interval_seconds": cfg.interval_seconds,
        "worker_index": cfg.worker_index,
        "total_workers": cfg.total_workers,
    }


def maybe_apply_stagger(cfg: StaggerConfig) -> float:
    """Apply stagger delay if enabled; return seconds slept (0.0 if skipped)."""
    if not cfg.enabled:
        return 0.0
    return apply_stagger(cfg)


def describe_stagger(cfg: StaggerConfig) -> str:
    """Return a human-readable summary of the stagger configuration."""
    if not cfg.enabled:
        return "stagger disabled"
    delay = compute_stagger_delay(cfg)
    return (
        f"stagger enabled: worker {cfg.worker_index}/{cfg.total_workers}, "
        f"delay={delay:.3f}s (interval={cfg.interval_seconds}s)"
    )


def validate_stagger_config(cfg: StaggerConfig) -> list[str]:
    """Validate a StaggerConfig and return a list of error messages.

    Returns an empty list if the configuration is valid.  Callers can
    treat a non-empty return value as a validation failure and surface
    the messages to the user before attempting to apply the stagger.
    """
    errors: list[str] = []
    if cfg.interval_seconds < 0:
        errors.append("interval_seconds must be >= 0")
    if cfg.total_workers < 1:
        errors.append("total_workers must be >= 1")
    if cfg.worker_index < 0:
        errors.append("worker_index must be >= 0")
    if cfg.worker_index >= cfg.total_workers:
        errors.append(
            f"worker_index ({cfg.worker_index}) must be less than "
            f"total_workers ({cfg.total_workers})"
        )
    return errors
