"""Hook that enforces the schedule gate before each retry attempt."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from retryctl.schedule import ScheduleConfig, is_within_schedule

log = logging.getLogger(__name__)


class ScheduleBlocked(Exception:
    """Raised when the schedule gate rejects execution."""


class ScheduleBlocked(Exception):
    """Raised when the schedule gate rejects execution."""


def enforce_schedule(
    cfg: ScheduleConfig,
    attempt: int,
    dt: Optional[datetime] = None,
    *,
    raise_on_block: bool = False,
) -> bool:
    """
    Check whether the current moment is inside a permitted schedule window.

    Parameters
    ----------
    cfg:
        The parsed schedule configuration.
    attempt:
        Current attempt number (1-based), used only for log context.
    dt:
        Override the current datetime (useful in tests).
    raise_on_block:
        If True, raise ScheduleBlocked instead of returning False.

    Returns
    -------
    bool
        True if execution is allowed, False otherwise.
    """
    now = dt or datetime.now()
    allowed = is_within_schedule(cfg, now)
    if not allowed:
        msg = (
            f"retryctl: attempt {attempt} skipped — outside schedule window "
            f"(time={now.strftime('%H:%M')}, tz={cfg.timezone})"
        )
        log.warning(msg)
        if raise_on_block:
            raise ScheduleBlocked(msg)
    return allowed


def describe_schedule(cfg: ScheduleConfig) -> str:
    """Return a human-readable summary of the schedule configuration."""
    if not cfg.enabled or not cfg.windows:
        return "schedule: disabled (always run)"
    lines = [f"schedule: {len(cfg.windows)} window(s), tz={cfg.timezone}"]
    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    for w in cfg.windows:
        days = ", ".join(day_names[d] for d in w.weekdays)
        lines.append(
            f"  {w.start.strftime('%H:%M')} – {w.end.strftime('%H:%M')} [{days}]"
        )
    return "\n".join(lines)
