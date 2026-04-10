"""Middleware helpers for integrating cooldown checks into the retry pipeline."""

from __future__ import annotations

import logging
from typing import Any

from retryctl.cooldown import CooldownConfig, CooldownBlocked, check_cooldown, record_success, clear_cooldown

log = logging.getLogger(__name__)


def parse_cooldown(config_dict: dict) -> CooldownConfig:
    """Build a CooldownConfig from the raw [cooldown] section of a config file."""
    section = config_dict.get("cooldown", {})
    if not isinstance(section, dict):
        raise TypeError("[cooldown] config section must be a mapping")
    return CooldownConfig.from_dict(section)


def cooldown_config_to_dict(cfg: CooldownConfig) -> dict:
    """Serialise a CooldownConfig back to a plain dict (useful for audit/debug)."""
    return {
        "enabled": cfg.enabled,
        "seconds": cfg.seconds,
        "key": cfg.key,
        "lock_dir": cfg.lock_dir,
    }


def enforce_cooldown_gate(cfg: CooldownConfig, command_key: str) -> None:
    """
    Check the cooldown gate before a run starts.

    Raises CooldownBlocked (and logs a warning) if still within the window.
    Does nothing when cooldown is disabled.
    """
    if not cfg.enabled:
        return
    try:
        check_cooldown(cfg, command_key)
    except CooldownBlocked as exc:
        log.warning("retryctl: %s", exc)
        raise


def on_run_success(cfg: CooldownConfig, command_key: str) -> None:
    """Record a successful run so the cooldown clock starts."""
    if not cfg.enabled:
        return
    record_success(cfg, command_key)
    log.debug("retryctl: cooldown started for key=%r (%.1fs)", command_key, cfg.seconds)


def on_run_reset(cfg: CooldownConfig, command_key: str) -> None:
    """Clear the cooldown state (e.g. when the operator wants to force a re-run)."""
    if not cfg.enabled:
        return
    clear_cooldown(cfg, command_key)
    log.debug("retryctl: cooldown cleared for key=%r", command_key)
