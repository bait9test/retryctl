"""Tests for retryctl.schedule and retryctl.schedule_middleware."""
from __future__ import annotations

import pytest
from datetime import datetime, time

from retryctl.schedule import (
    ScheduleConfig,
    ScheduleWindow,
    from_dict,
    is_within_schedule,
    _parse_time,
    _parse_weekdays,
)
from retryctl.schedule_middleware import (
    parse_schedule,
    schedule_config_to_dict,
    check_schedule_gate,
)


# ---------------------------------------------------------------------------
# _parse_time
# ---------------------------------------------------------------------------

def test_parse_time_valid():
    assert _parse_time("09:30") == time(9, 30)


def test_parse_time_leading_zero():
    assert _parse_time("00:00") == time(0, 0)


def test_parse_time_invalid_raises():
    with pytest.raises(ValueError, match="Invalid time format"):
        _parse_time("9am")


# ---------------------------------------------------------------------------
# _parse_weekdays
# ---------------------------------------------------------------------------

def test_parse_weekdays_none_returns_all():
    assert _parse_weekdays(None) == list(range(7))


def test_parse_weekdays_named():
    assert _parse_weekdays(["Mon", "Wed", "Fri"]) == [0, 2, 4]


def test_parse_weekdays_unknown_raises():
    with pytest.raises(ValueError, match="Unknown weekday"):
        _parse_weekdays(["Mon", "Xyz"])


# ---------------------------------------------------------------------------
# ScheduleWindow.contains
# ---------------------------------------------------------------------------

def test_window_contains_inside():
    w = ScheduleWindow(start=time(9, 0), end=time(17, 0))
    assert w.contains(datetime(2024, 1, 15, 12, 0))  # Monday noon


def test_window_contains_outside():
    w = ScheduleWindow(start=time(9, 0), end=time(17, 0))
    assert not w.contains(datetime(2024, 1, 15, 20, 0))


def test_window_overnight_span():
    w = ScheduleWindow(start=time(22, 0), end=time(6, 0))
    assert w.contains(datetime(2024, 1, 15, 23, 30))
    assert w.contains(datetime(2024, 1, 15, 5, 0))
    assert not w.contains(datetime(2024, 1, 15, 12, 0))


def test_window_weekday_filter():
    w = ScheduleWindow(start=time(9, 0), end=time(17, 0), weekdays=[0, 1, 2, 3, 4])
    # Saturday = 5
    assert not w.contains(datetime(2024, 1, 20, 12, 0))


# ---------------------------------------------------------------------------
# from_dict
# ---------------------------------------------------------------------------

def test_from_dict_defaults():
    cfg = from_dict({})
    assert not cfg.enabled
    assert cfg.windows == []
    assert cfg.timezone == "local"


def test_from_dict_single_window():
    cfg = from_dict({"windows": [{"start": "08:00", "end": "18:00"}]})
    assert cfg.enabled  # auto-enabled when windows present
    assert len(cfg.windows) == 1
    assert cfg.windows[0].start == time(8, 0)


def test_from_dict_invalid_windows_type():
    with pytest.raises(TypeError):
        from_dict({"windows": "bad"})


# ---------------------------------------------------------------------------
# is_within_schedule
# ---------------------------------------------------------------------------

def test_disabled_always_allows():
    cfg = ScheduleConfig(enabled=False)
    assert is_within_schedule(cfg, datetime(2024, 1, 15, 3, 0))


def test_no_windows_always_allows():
    cfg = ScheduleConfig(enabled=True, windows=[])
    assert is_within_schedule(cfg)


def test_within_window_returns_true():
    cfg = from_dict({"windows": [{"start": "09:00", "end": "17:00"}]})
    assert is_within_schedule(cfg, datetime(2024, 1, 15, 10, 0))


def test_outside_window_returns_false():
    cfg = from_dict({"windows": [{"start": "09:00", "end": "17:00"}]})
    assert not is_within_schedule(cfg, datetime(2024, 1, 15, 20, 0))


# ---------------------------------------------------------------------------
# middleware helpers
# ---------------------------------------------------------------------------

def test_parse_schedule_from_config():
    raw = {"schedule": {"windows": [{"start": "06:00", "end": "22:00"}]}}
    cfg = parse_schedule(raw)
    assert cfg.enabled
    assert len(cfg.windows) == 1


def test_parse_schedule_missing_section_returns_defaults():
    cfg = parse_schedule({})
    assert not cfg.enabled


def test_schedule_config_to_dict_roundtrip():
    raw = {"windows": [{"start": "08:00", "end": "20:00", "weekdays": ["Mon", "Fri"]}]}
    cfg = from_dict(raw)
    d = schedule_config_to_dict(cfg)
    assert d["windows"][0]["start"] == "08:00"
    assert d["windows"][0]["weekdays"] == [0, 4]


def test_check_schedule_gate_allows(caplog):
    cfg = from_dict({"windows": [{"start": "00:00", "end": "23:59"}]})
    result = check_schedule_gate(cfg, datetime(2024, 1, 15, 12, 0))
    assert result is True
    assert "blocked" not in caplog.text


def test_check_schedule_gate_blocks(caplog):
    import logging
    cfg = from_dict({"windows": [{"start": "09:00", "end": "10:00"}]})
    with caplog.at_level(logging.WARNING):
        result = check_schedule_gate(cfg, datetime(2024, 1, 15, 22, 0))
    assert result is False
    assert "blocked" in caplog.text
