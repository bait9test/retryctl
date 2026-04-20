"""Tests for retryctl.flap and retryctl.flap_middleware."""
from __future__ import annotations

import time
import pytest

from retryctl.flap import (
    FlapConfig,
    FlapDetected,
    FlapTracker,
    clear_registry,
    get_tracker,
)
from retryctl.flap_middleware import (
    describe_flap,
    flap_config_to_dict,
    make_tracker,
    on_attempt_complete,
    parse_flap,
)


@pytest.fixture(autouse=True)
def _clean():
    clear_registry()
    yield
    clear_registry()


# --- FlapConfig ---

def test_config_defaults():
    cfg = FlapConfig()
    assert cfg.enabled is False
    assert cfg.threshold == 4
    assert cfg.window_seconds == 60.0


def test_from_dict_full():
    cfg = FlapConfig.from_dict({"enabled": True, "threshold": 3, "window_seconds": 30.0})
    assert cfg.enabled is True
    assert cfg.threshold == 3
    assert cfg.window_seconds == 30.0


def test_from_dict_empty_uses_defaults():
    cfg = FlapConfig.from_dict({})
    assert cfg.threshold == 4
    assert cfg.window_seconds == 60.0


def test_from_dict_auto_enables_when_threshold_set():
    cfg = FlapConfig.from_dict({"threshold": 2})
    assert cfg.enabled is True


def test_from_dict_invalid_type_raises():
    with pytest.raises(TypeError):
        FlapConfig.from_dict("bad")


def test_from_dict_zero_threshold_raises():
    with pytest.raises(ValueError):
        FlapConfig.from_dict({"threshold": 0})


def test_from_dict_negative_window_raises():
    with pytest.raises(ValueError):
        FlapConfig.from_dict({"threshold": 2, "window_seconds": -1})


# --- FlapTracker ---

def test_no_flap_stable_failures():
    cfg = FlapConfig(enabled=True, threshold=3, window_seconds=60)
    t = FlapTracker(cfg, "k")
    for _ in range(5):
        t.record(False)  # no transitions
    assert t.transition_count == 0


def test_transitions_counted():
    cfg = FlapConfig(enabled=True, threshold=10, window_seconds=60)
    t = FlapTracker(cfg, "k")
    t.record(True)
    t.record(False)
    t.record(True)
    assert t.transition_count == 2


def test_flap_detected_at_threshold():
    cfg = FlapConfig(enabled=True, threshold=2, window_seconds=60)
    t = FlapTracker(cfg, "k")
    t.record(True)
    t.record(False)  # transition 1
    with pytest.raises(FlapDetected) as exc_info:
        t.record(True)  # transition 2 -> threshold reached
    assert "k" in str(exc_info.value)


def test_disabled_tracker_never_raises():
    cfg = FlapConfig(enabled=False, threshold=1, window_seconds=60)
    t = FlapTracker(cfg, "k")
    for _ in range(20):
        t.record(True)
        t.record(False)
    assert t.transition_count == 0


def test_old_transitions_evicted(monkeypatch):
    cfg = FlapConfig(enabled=True, threshold=3, window_seconds=1)
    t = FlapTracker(cfg, "k")
    t.record(True)
    t.record(False)  # transition at t=0
    monkeypatch.setattr(time, "monotonic", lambda: time.monotonic.__wrapped__() + 2)
    assert t.transition_count == 0  # evicted


# --- middleware ---

def test_parse_flap_missing_section_uses_defaults():
    cfg = parse_flap({})
    assert cfg.enabled is False


def test_parse_flap_full_section():
    cfg = parse_flap({"flap": {"threshold": 3, "window_seconds": 45}})
    assert cfg.threshold == 3
    assert cfg.window_seconds == 45


def test_parse_flap_invalid_type_raises():
    with pytest.raises(TypeError):
        parse_flap({"flap": "bad"})


def test_flap_config_to_dict_roundtrip():
    cfg = FlapConfig(enabled=True, threshold=5, window_seconds=120)
    d = flap_config_to_dict(cfg)
    assert d["threshold"] == 5
    assert d["window_seconds"] == 120
    assert d["enabled"] is True


def test_make_tracker_returns_same_instance():
    cfg = FlapConfig(enabled=True, threshold=4, window_seconds=60)
    t1 = make_tracker(cfg, "mykey")
    t2 = make_tracker(cfg, "mykey")
    assert t1 is t2


def test_on_attempt_complete_raises_on_flap():
    cfg = FlapConfig(enabled=True, threshold=2, window_seconds=60)
    t = FlapTracker(cfg, "x")
    t.record(True)
    t.record(False)  # transition 1
    with pytest.raises(FlapDetected):
        on_attempt_complete(t, True)  # transition 2


def test_describe_flap_disabled():
    assert "disabled" in describe_flap(FlapConfig(enabled=False))


def test_describe_flap_enabled():
    desc = describe_flap(FlapConfig(enabled=True, threshold=3, window_seconds=30))
    assert "3" in desc
    assert "30" in desc
