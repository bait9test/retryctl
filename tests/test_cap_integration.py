"""Integration-style tests: CapTracker used inside a simulated retry loop."""
from __future__ import annotations

import pytest

from retryctl.cap import CapConfig, CapExceeded, CapTracker
from retryctl.cap_middleware import enforce_cap_gate, on_attempt_consumed


def _make_tracker(max_attempts: int, per_key: bool = False) -> CapTracker:
    cfg = CapConfig(enabled=True, max_attempts=max_attempts, per_key=per_key)
    return CapTracker(config=cfg)


def _run_loop(tracker: CapTracker, total_runs: int, label: str = "__global__") -> int:
    """Simulate a retry loop; returns how many attempts actually ran."""
    ran = 0
    for _ in range(total_runs):
        try:
            enforce_cap_gate(tracker, label)
        except CapExceeded:
            break
        on_attempt_consumed(tracker, label)
        ran += 1
    return ran


def test_loop_stops_at_cap():
    t = _make_tracker(3)
    ran = _run_loop(t, total_runs=10)
    assert ran == 3


def test_loop_completes_when_under_cap():
    t = _make_tracker(10)
    ran = _run_loop(t, total_runs=4)
    assert ran == 4


def test_disabled_cap_never_blocks():
    cfg = CapConfig(enabled=False)
    t = CapTracker(config=cfg)
    ran = _run_loop(t, total_runs=50)
    assert ran == 50


def test_per_key_caps_independently():
    t = _make_tracker(2, per_key=True)
    ran_a = _run_loop(t, total_runs=10, label="a")
    ran_b = _run_loop(t, total_runs=10, label="b")
    assert ran_a == 2
    assert ran_b == 2


def test_cap_exceeded_error_message():
    t = _make_tracker(1)
    enforce_cap_gate(t)
    on_attempt_consumed(t)
    with pytest.raises(CapExceeded) as exc_info:
        enforce_cap_gate(t)
    assert "1" in str(exc_info.value)
    assert "__global__" in str(exc_info.value)
