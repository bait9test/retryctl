"""Helpers for wiring DecayTracker into the retry loop."""
from __future__ import annotations

from typing import Any

from retryctl.decay import DecayConfig, DecayTracker


def parse_decay(config_dict: dict) -> DecayConfig:
    """Extract [decay] section from the top-level config mapping."""
    section = config_dict.get("decay", {})
    if not isinstance(section, dict):
        raise TypeError("[decay] must be a TOML table")
    return DecayConfig.from_dict(section)


def decay_config_to_dict(cfg: DecayConfig) -> dict:
    """Serialise a DecayConfig back to a plain dict (useful for audit/replay)."""
    return {
        "enabled": cfg.enabled,
        "threshold": cfg.threshold,
        "factor": cfg.factor,
        "max_multiplier": cfg.max_multiplier,
    }


def apply_decay(tracker: DecayTracker, base_delay: float) -> float:
    """Scale *base_delay* by the tracker's current multiplier.

    Call this after computing the normal backoff delay but before sleeping.
    """
    return tracker.apply(base_delay)


def on_attempt_failure(tracker: DecayTracker) -> None:
    """Notify the tracker that the latest attempt failed."""
    tracker.record_failure()


def on_run_success(tracker: DecayTracker) -> None:
    """Reset the failure streak on a successful run."""
    tracker.record_success()


def describe_decay(cfg: DecayConfig) -> str:
    if not cfg.enabled:
        return "decay: disabled"
    return (
        f"decay: enabled (threshold={cfg.threshold}, "
        f"factor={cfg.factor}, max_multiplier={cfg.max_multiplier})"
    )
