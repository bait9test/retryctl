"""Schedule-based retry gating — skip execution outside allowed windows."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, time
from typing import List, Optional, Tuple


@dataclass
class ScheduleWindow:
    start: time
    end: time
    weekdays: List[int] = field(default_factory=lambda: list(range(7)))  # 0=Mon

    def contains(self, dt: datetime) -> bool:
        if dt.weekday() not in self.weekdays:
            return False
        t = dt.time().replace(second=0, microsecond=0)
        if self.start <= self.end:
            return self.start <= t <= self.end
        # overnight window e.g. 22:00 – 06:00
        return t >= self.start or t <= self.end


@dataclass
class ScheduleConfig:
    enabled: bool = False
    windows: List[ScheduleWindow] = field(default_factory=list)
    timezone: str = "local"


_TIME_RE = re.compile(r"^(\d{1,2}):(\d{2})$")
_DAY_NAMES = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def _parse_time(s: str) -> time:
    m = _TIME_RE.match(s.strip())
    if not m:
        raise ValueError(f"Invalid time format: {s!r} (expected HH:MM)")
    return time(int(m.group(1)), int(m.group(2)))


def _parse_weekdays(raw: Optional[List[str]]) -> List[int]:
    if not raw:
        return list(range(7))
    result = []
    for d in raw:
        dl = d.strip().lower()[:3]
        if dl not in _DAY_NAMES:
            raise ValueError(f"Unknown weekday: {d!r}")
        result.append(_DAY_NAMES.index(dl))
    return result


def from_dict(data: dict) -> ScheduleConfig:
    raw_windows = data.get("windows", [])
    if not isinstance(raw_windows, list):
        raise TypeError("schedule.windows must be a list")
    windows: List[ScheduleWindow] = []
    for w in raw_windows:
        windows.append(ScheduleWindow(
            start=_parse_time(w["start"]),
            end=_parse_time(w["end"]),
            weekdays=_parse_weekdays(w.get("weekdays")),
        ))
    return ScheduleConfig(
        enabled=bool(data.get("enabled", bool(windows))),
        windows=windows,
        timezone=str(data.get("timezone", "local")),
    )


def is_within_schedule(cfg: ScheduleConfig, dt: Optional[datetime] = None) -> bool:
    """Return True if *dt* (default: now) falls inside any configured window."""
    if not cfg.enabled or not cfg.windows:
        return True
    now = dt or datetime.now()
    return any(w.contains(now) for w in cfg.windows)
