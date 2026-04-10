"""Integration-style tests: schedule parsing wired through config dict."""
from __future__ import annotations

from datetime import datetime

import pytest

from retryctl.schedule import from_dict, is_within_schedule
from retryctl.schedule_middleware import parse_schedule, check_schedule_gate


def _cfg(raw: dict):
    return parse_schedule({"schedule": raw})


def test_multi_window_first_matches():
    cfg = _cfg({
        "windows": [
            {"start": "06:00", "end": "08:00"},
            {"start": "18:00", "end": "22:00"},
        ]
    })
    assert is_within_schedule(cfg, datetime(2024, 3, 4, 7, 0))


def test_multi_window_second_matches():
    cfg = _cfg({
        "windows": [
            {"start": "06:00", "end": "08:00"},
            {"start": "18:00", "end": "22:00"},
        ]
    })
    assert is_within_schedule(cfg, datetime(2024, 3, 4, 20, 0))


def test_multi_window_neither_matches():
    cfg = _cfg({
        "windows": [
            {"start": "06:00", "end": "08:00"},
            {"start": "18:00", "end": "22:00"},
        ]
    })
    assert not is_within_schedule(cfg, datetime(2024, 3, 4, 12, 0))


def test_weekday_restricted_window_weekday_ok():
    cfg = _cfg({
        "windows": [
            {"start": "09:00", "end": "17:00", "weekdays": ["Mon", "Tue", "Wed", "Thu", "Fri"]}
        ]
    })
    # 2024-03-04 is a Monday
    assert is_within_schedule(cfg, datetime(2024, 3, 4, 12, 0))


def test_weekday_restricted_window_weekend_blocked():
    cfg = _cfg({
        "windows": [
            {"start": "09:00", "end": "17:00", "weekdays": ["Mon", "Tue", "Wed", "Thu", "Fri"]}
        ]
    })
    # 2024-03-09 is a Saturday
    assert not is_within_schedule(cfg, datetime(2024, 3, 9, 12, 0))


def test_timezone_field_preserved():
    cfg = _cfg({"timezone": "UTC", "windows": [{"start": "00:00", "end": "23:59"}]})
    assert cfg.timezone == "UTC"


def test_explicit_enabled_false_disables_gate():
    cfg = _cfg({
        "enabled": False,
        "windows": [{"start": "09:00", "end": "10:00"}],
    })
    # Even though we're outside the window, disabled means always allowed
    assert is_within_schedule(cfg, datetime(2024, 3, 4, 22, 0))


def test_gate_returns_false_and_warns(caplog):
    import logging
    cfg = _cfg({"windows": [{"start": "09:00", "end": "10:00"}]})
    with caplog.at_level(logging.WARNING):
        ok = check_schedule_gate(cfg, datetime(2024, 3, 4, 22, 0))
    assert not ok
    assert "schedule gate" in caplog.text
