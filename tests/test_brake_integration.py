"""Integration tests: brake delay accumulates correctly across a simulated loop."""
from __future__ import annotations

from retryctl.brake import BrakeConfig, BrakeState
from retryctl.brake_middleware import on_attempt_failure, on_run_success


def _simulate_loop(
    cfg: BrakeConfig,
    outcomes: list[bool],  # True = success, False = failure
) -> list[int]:
    """Return list of extra_ms values recorded after each attempt."""
    state = BrakeState()
    delays = []
    for success in outcomes:
        if success:
            on_run_success(cfg, state)
            delays.append(state.extra_ms)
        else:
            extra = on_attempt_failure(cfg, state)
            delays.append(extra)
    return delays


def test_no_braking_when_always_succeeds():
    cfg = BrakeConfig(enabled=True, threshold=2, step_ms=200, max_ms=2000)
    delays = _simulate_loop(cfg, [True, True, True])
    assert all(d == 0 for d in delays)


def test_brake_kicks_in_after_threshold():
    cfg = BrakeConfig(enabled=True, threshold=2, step_ms=100, max_ms=1000)
    # 2 failures = no brake; 3rd failure triggers first step
    delays = _simulate_loop(cfg, [False, False, False])
    assert delays[0] == 0
    assert delays[1] == 0
    assert delays[2] == 100


def test_brake_resets_after_success():
    cfg = BrakeConfig(enabled=True, threshold=1, step_ms=150, max_ms=1000)
    # failure x3 then success should reset
    delays = _simulate_loop(cfg, [False, False, False, True])
    assert delays[-1] == 0  # after success, extra_ms is 0


def test_brake_caps_at_max():
    cfg = BrakeConfig(enabled=True, threshold=1, step_ms=300, max_ms=500)
    delays = _simulate_loop(cfg, [False, False, False, False])
    # After threshold (1), each failure adds 300 capped at 500
    assert delays[1] == 300   # 2nd failure: first brake step
    assert delays[2] == 500   # 3rd failure: 600 -> capped 500
    assert delays[3] == 500   # stays at cap


def test_disabled_brake_never_adds_delay():
    cfg = BrakeConfig(enabled=False, threshold=1, step_ms=999, max_ms=9999)
    delays = _simulate_loop(cfg, [False] * 10)
    assert all(d == 0 for d in delays)
