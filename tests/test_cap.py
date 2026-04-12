"""Unit tests for retryctl.cap and retryctl.cap_middleware."""
from __future__ import annotations

import pytest

from retryctl.cap import CapConfig, CapExceeded, CapTracker
from retryctl.cap_middleware import (
    cap_config_to_dict,
    describe_cap,
    enforce_cap_gate,
    on_attempt_consumed,
    parse_cap,
)


# ---------------------------------------------------------------------------
# CapConfig.from_dict
# ---------------------------------------------------------------------------

def test_config_defaults():
    cfg = CapConfig.from_dict({})
    assert cfg.enabled is False
    assert cfg.max_attempts is None
    assert cfg.per_key is False


def test_config_from_dict_full():
    cfg = CapConfig.from_dict({"max_attempts": 5, "per_key": True, "enabled": True})
    assert cfg.enabled is True
    assert cfg.max_attempts == 5
    assert cfg.per_key is True


def test_config_auto_enables_when_max_set():
    cfg = CapConfig.from_dict({"max_attempts": 3})
    assert cfg.enabled is True


def test_config_from_dict_invalid_type_raises():
    with pytest.raises(TypeError):
        CapConfig.from_dict("not-a-dict")  # type: ignore[arg-type]


def test_config_zero_max_raises():
    with pytest.raises(ValueError):
        CapConfig.from_dict({"max_attempts": 0})


def test_config_negative_max_raises():
    with pytest.raises(ValueError):
        CapConfig.from_dict({"max_attempts": -1})


# ---------------------------------------------------------------------------
# CapTracker behaviour
# ---------------------------------------------------------------------------

def _tracker(max_attempts: int, per_key: bool = False) -> CapTracker:
    cfg = CapConfig(enabled=True, max_attempts=max_attempts, per_key=per_key)
    return CapTracker(config=cfg)


def test_disabled_tracker_always_allows():
    cfg = CapConfig(enabled=False)
    t = CapTracker(config=cfg)
    for _ in range(100):
        assert t.is_allowed() is True
        t.consume()


def test_allows_up_to_max():
    t = _tracker(3)
    for _ in range(3):
        assert t.is_allowed() is True
        t.consume()
    assert t.is_allowed() is False


def test_remaining_counts_down():
    t = _tracker(4)
    assert t.remaining() == 4
    t.consume()
    assert t.remaining() == 3
    t.consume()
    assert t.remaining() == 2


def test_remaining_never_negative():
    t = _tracker(1)
    t.consume()
    t.consume()  # over the limit
    assert t.remaining() == 0


def test_per_key_tracks_independently():
    t = _tracker(2, per_key=True)
    t.consume("job-a")
    t.consume("job-a")
    assert t.is_allowed("job-a") is False
    assert t.is_allowed("job-b") is True


def test_enforce_raises_cap_exceeded():
    t = _tracker(1)
    t.enforce()  # first attempt — ok
    with pytest.raises(CapExceeded) as exc_info:
        t.enforce()  # second attempt — over cap
    assert exc_info.value.limit == 1


# ---------------------------------------------------------------------------
# cap_middleware helpers
# ---------------------------------------------------------------------------

def test_parse_cap_empty_config():
    cfg = parse_cap({})
    assert cfg.enabled is False


def test_parse_cap_full_section():
    cfg = parse_cap({"cap": {"max_attempts": 7, "per_key": False}})
    assert cfg.max_attempts == 7


def test_parse_cap_invalid_type_raises():
    with pytest.raises(TypeError):
        parse_cap({"cap": "bad"})


def test_cap_config_to_dict_roundtrip():
    cfg = CapConfig(enabled=True, max_attempts=10, per_key=True)
    d = cap_config_to_dict(cfg)
    assert d == {"enabled": True, "max_attempts": 10, "per_key": True}


def test_enforce_cap_gate_raises_when_exhausted():
    cfg = CapConfig(enabled=True, max_attempts=2)
    t = CapTracker(config=cfg)
    on_attempt_consumed(t)
    on_attempt_consumed(t)
    with pytest.raises(CapExceeded):
        enforce_cap_gate(t)


def test_enforce_cap_gate_passes_when_disabled():
    cfg = CapConfig(enabled=False)
    t = CapTracker(config=cfg)
    enforce_cap_gate(t)  # should not raise


def test_describe_cap_disabled():
    assert describe_cap(CapConfig()) == "cap: disabled"


def test_describe_cap_enabled():
    cfg = CapConfig(enabled=True, max_attempts=5, per_key=False)
    assert "5" in describe_cap(cfg)
    assert "global" in describe_cap(cfg)


def test_describe_cap_per_key():
    cfg = CapConfig(enabled=True, max_attempts=3, per_key=True)
    assert "per-key" in describe_cap(cfg)
