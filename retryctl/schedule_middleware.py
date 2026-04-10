"""Middleware that blocks retries outside scheduled windows."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from retryctl.schedule import ScheduleConfig, from_dict, is_within_schedule

log = logging.getLogger(__name__)


def parse_schedule(config: dict) -> ScheduleConfig:
    """Extract and parse the [schedule] section from a raw config dict."""
    raw = config.get("schedule", {})
    if not isinstance(raw, dict):
        raise TypeError("[schedule] config must be a mapping")
    return from_dict(raw)


def schedule_config_to_dict(cfg: ScheduleConfig) -> dict:
    """Serialise a ScheduleConfig back to a plain dict (for merging/export)."""
    return {
        "enabled": cfg.enabled,
        "timezone": cfg.timezone,
        "windows": [
            {
                "start": w.start.strftime("%H:%M"),
                "end": w.end.strftime("%H:%M"),
                "weekdays": w.weekdays,
            }
            for w in cfg.windows
        ],
    }


def check_schedule_gate(
    cfg: ScheduleConfig,
    dt: Optional[datetime] = None,
) -> bool:
    """
    Return True if execution should proceed, False if it should be skipped.
    Logs a warning when execution is blocked.
    """
    allowed = is_within_schedule(cfg, dt)
    if not allowed:
        now = dt or datetime.now()
        log.warning(
            "retryctl: execution blocked by schedule gate (current time %s, "
            "timezone=%s)",
            now.strftime("%Y-%m-%d %H:%M"),
            cfg.timezone,
        )
    return allowed
