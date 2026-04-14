"""Tests for retryctl.stamp and retryctl.stamp_middleware."""
from __future__ import annotations

import pytest

from retryctl.stamp import AttemptStamp, StampConfig, StampTracker
from retryctl.stamp_middleware import (
    before_attempt,
    describe_stamp,
    make_tracker,
    parse_stamp,
    stamp_config_to_dict,
)


# ---------------------------------------------------------------------------
# StampConfig
# ---------------------------------------------------------------------------

def test_config_defaults():
    cfg = StampConfig()
    assert cfg.enabled is False
    assert cfg.include_monotonic is False


def test_from_dict_full():
    cfg = StampConfig.from_dict({"enabled": True, "include_monotonic": True})
    assert cfg.enabled is True
    assert cfg.include_monotonic is True


def test_from_dict_empty_uses_defaults():
    cfg = StampConfig.from_dict({})
    assert cfg.enabled is False
    assert cfg.include_monotonic is False


def test_from_dict_invalid_type_raises():
    with pytest.raises(TypeError):
        StampConfig.from_dict("bad")


def test_from_dict_coerces_to_bool():
    cfg = StampConfig.from_dict({"enabled": 1, "include_monotonic": 0})
    assert cfg.enabled is True
    assert cfg.include_monotonic is False


# ---------------------------------------------------------------------------
# AttemptStamp
# ---------------------------------------------------------------------------

def test_attempt_stamp_to_dict_no_monotonic():
    s = AttemptStamp(attempt=1, wall=1_000.0)
    d = s.to_dict()
    assert d == {"attempt": 1, "wall": 1_000.0}
    assert "monotonic" not in d


def test_attempt_stamp_to_dict_with_monotonic():
    s = AttemptStamp(attempt=2, wall=2_000.0, monotonic=500.0)
    d = s.to_dict()
    assert d["monotonic"] == 500.0


# ---------------------------------------------------------------------------
# StampTracker
# ---------------------------------------------------------------------------

def test_disabled_tracker_returns_none():
    tracker = StampTracker(config=StampConfig(enabled=False))
    result = tracker.record(1)
    assert result is None
    assert tracker.stamps == []


def test_enabled_tracker_records_stamp():
    tracker = StampTracker(config=StampConfig(enabled=True))
    stamp = tracker.record(1)
    assert stamp is not None
    assert stamp.attempt == 1
    assert stamp.wall > 0
    assert stamp.monotonic is None


def test_tracker_with_monotonic():
    tracker = StampTracker(config=StampConfig(enabled=True, include_monotonic=True))
    stamp = tracker.record(1)
    assert stamp.monotonic is not None
    assert stamp.monotonic > 0


def test_tracker_get_returns_correct_stamp():
    tracker = StampTracker(config=StampConfig(enabled=True))
    tracker.record(1)
    tracker.record(2)
    s = tracker.get(2)
    assert s is not None
    assert s.attempt == 2


def test_tracker_get_missing_returns_none():
    tracker = StampTracker(config=StampConfig(enabled=True))
    assert tracker.get(99) is None


def test_tracker_to_list():
    tracker = StampTracker(config=StampConfig(enabled=True))
    tracker.record(1)
    tracker.record(2)
    lst = tracker.to_list()
    assert len(lst) == 2
    assert lst[0]["attempt"] == 1


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

def test_parse_stamp_empty_config():
    cfg = parse_stamp({})
    assert cfg.enabled is False


def test_parse_stamp_full_section():
    cfg = parse_stamp({"stamp": {"enabled": True, "include_monotonic": True}})
    assert cfg.enabled is True
    assert cfg.include_monotonic is True


def test_parse_stamp_invalid_section_raises():
    with pytest.raises(TypeError):
        parse_stamp({"stamp": "bad"})


def test_stamp_config_to_dict_roundtrip():
    cfg = StampConfig(enabled=True, include_monotonic=True)
    d = stamp_config_to_dict(cfg)
    assert d == {"enabled": True, "include_monotonic": True}


def test_make_tracker_returns_tracker():
    cfg = StampConfig(enabled=True)
    tracker = make_tracker(cfg)
    assert isinstance(tracker, StampTracker)


def test_before_attempt_records_stamp():
    cfg = StampConfig(enabled=True)
    tracker = make_tracker(cfg)
    before_attempt(tracker, 3)
    assert tracker.get(3) is not None


def test_describe_stamp_disabled():
    assert describe_stamp(StampConfig()) == "stamp: disabled"


def test_describe_stamp_enabled_no_monotonic():
    assert describe_stamp(StampConfig(enabled=True)) == "stamp: enabled"


def test_describe_stamp_enabled_with_monotonic():
    desc = describe_stamp(StampConfig(enabled=True, include_monotonic=True))
    assert "monotonic=yes" in desc
