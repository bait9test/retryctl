"""Integration-style tests: simulate a full retry loop with flap detection."""
from __future__ import annotations

import pytest

from retryctl.flap import (
    FlapConfig,
    FlapDetected,
    FlapTracker,
    clear_registry,
)


@pytest.fixture(autouse=True)
def _clean():
    clear_registry()
    yield
    clear_registry()


def _simulate_loop(outcomes: list[bool], cfg: FlapConfig, key: str = "cmd") -> list[str]:
    """Simulate a retry loop; returns list of events ('ok', 'fail', 'flap')."""
    tracker = FlapTracker(cfg, key)
    events: list[str] = []
    for success in outcomes:
        try:
            tracker.record(success)
            events.append("ok" if success else "fail")
        except FlapDetected:
            events.append("flap")
            break
    return events


def test_stable_failure_never_flaps():
    cfg = FlapConfig(enabled=True, threshold=3, window_seconds=60)
    events = _simulate_loop([False] * 10, cfg)
    assert "flap" not in events
    assert len(events) == 10


def test_alternating_triggers_flap():
    cfg = FlapConfig(enabled=True, threshold=3, window_seconds=60)
    # T F T F → transitions at positions 2,3,4 → flap on 4th record
    events = _simulate_loop([True, False, True, False, True], cfg)
    assert events[-1] == "flap"


def test_flap_stops_loop_early():
    cfg = FlapConfig(enabled=True, threshold=2, window_seconds=60)
    outcomes = [True, False, True, False, True, False]
    events = _simulate_loop(outcomes, cfg)
    # loop must stop before processing all outcomes
    assert len(events) < len(outcomes)
    assert events[-1] == "flap"


def test_disabled_config_never_flaps():
    cfg = FlapConfig(enabled=False, threshold=1, window_seconds=60)
    outcomes = [True, False] * 20
    events = _simulate_loop(outcomes, cfg)
    assert "flap" not in events


def test_different_keys_independent():
    cfg = FlapConfig(enabled=True, threshold=2, window_seconds=60)
    t1 = FlapTracker(cfg, "key1")
    t2 = FlapTracker(cfg, "key2")
    # drive key1 to flap
    t1.record(True)
    t1.record(False)
    with pytest.raises(FlapDetected):
        t1.record(True)
    # key2 should be unaffected
    t2.record(True)
    t2.record(False)  # only 1 transition, no flap yet
    assert t2.transition_count == 1
