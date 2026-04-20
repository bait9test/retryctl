"""damp_middleware.py – wiring helpers for the damp feature."""
from __future__ import annotations

from typing import Any, Dict

from retryctl.damp import DampConfig, DampTracker


def parse_damp(raw_config: Dict[str, Any]) -> DampConfig:
    """Extract [damp] section from the parsed TOML config dict."""
    section = raw_config.get("damp")
    if section is None:
        return DampConfig()
    return DampConfig.from_dict(section)


def damp_config_to_dict(cfg: DampConfig) -> Dict[str, Any]:
    """Serialise a DampConfig back to a plain dict (for audit / snapshot)."""
    return {
        "enabled": cfg.enabled,
        "threshold": cfg.threshold,
        "window_seconds": cfg.window_seconds,
        "fingerprint_stderr": cfg.fingerprint_stderr,
    }


def make_tracker(cfg: DampConfig) -> DampTracker:
    """Convenience factory so callers don't import DampTracker directly."""
    return DampTracker(cfg)


def on_attempt_failure(
    tracker: DampTracker,
    exit_code: int,
    stderr: str | None = None,
) -> None:
    """Call after each failed attempt; may raise DampedAttempt."""
    tracker.record_failure(exit_code, stderr)


def on_run_success(tracker: DampTracker) -> None:
    """Call when the overall run succeeds to reset internal state."""
    tracker.record_success()


def describe_damp(cfg: DampConfig) -> str:
    if not cfg.enabled:
        return "damp: disabled"
    return (
        f"damp: threshold={cfg.threshold} identical failures "
        f"within {cfg.window_seconds}s triggers damping"
    )
