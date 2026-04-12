"""Helpers for wiring CapTracker into the CLI / config pipeline."""
from __future__ import annotations

from typing import Any, Dict

from retryctl.cap import CapConfig, CapTracker


def parse_cap(raw_config: Dict[str, Any]) -> CapConfig:
    """Extract [cap] section from a raw config dict."""
    section = raw_config.get("cap", {})
    if not isinstance(section, dict):
        raise TypeError(f"[cap] must be a table, got {type(section).__name__}")
    return CapConfig.from_dict(section)


def cap_config_to_dict(cfg: CapConfig) -> Dict[str, Any]:
    """Serialise a CapConfig back to a plain dict (for audit/debug)."""
    return {
        "enabled": cfg.enabled,
        "max_attempts": cfg.max_attempts,
        "per_key": cfg.per_key,
    }


def enforce_cap_gate(tracker: CapTracker, label: str = "__global__") -> None:
    """Check the cap *before* an attempt; raise CapExceeded if exhausted.

    Unlike ``tracker.enforce`` this does NOT consume a slot — it only checks.
    Call ``on_attempt_consumed`` after the attempt to record usage.
    """
    if not tracker.config.enabled or tracker.config.max_attempts is None:
        return
    if not tracker.is_allowed(label):
        from retryctl.cap import CapExceeded
        raise CapExceeded(label, tracker.config.max_attempts)  # type: ignore[arg-type]


def on_attempt_consumed(tracker: CapTracker, label: str = "__global__") -> None:
    """Record that one attempt has been used."""
    tracker.consume(label)


def describe_cap(cfg: CapConfig) -> str:
    if not cfg.enabled:
        return "cap: disabled"
    scope = "per-key" if cfg.per_key else "global"
    return f"cap: max {cfg.max_attempts} attempts ({scope})"
