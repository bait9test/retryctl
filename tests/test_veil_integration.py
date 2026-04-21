"""Integration tests: veil interacting with a simulated retry loop."""
from __future__ import annotations

import pytest

from retryctl.veil import VeilConfig, VeilTracker, VeiledAttempt


def _run_loop(
    cfg: VeilConfig,
    max_attempts: int = 20,
    always_fail: bool = True,
) -> tuple[int, int]:
    """Simulate a retry loop; return (attempts_run, attempts_veiled)."""
    tracker = VeilTracker(config=cfg)
    run = 0
    veiled = 0
    for i in range(1, max_attempts + 1):
        try:
            tracker.check(i)
        except VeiledAttempt:
            veiled += 1
            continue
        run += 1
        if not always_fail:
            break  # success path
    return run, veiled


def test_disabled_veil_runs_all_attempts():
    cfg = VeilConfig(enabled=False, drop_rate=0.5, seed=0)
    run, veiled = _run_loop(cfg, max_attempts=10)
    assert veiled == 0
    assert run == 10


def test_full_drop_rate_veils_all():
    cfg = VeilConfig(enabled=True, drop_rate=1.0, seed=0)
    run, veiled = _run_loop(cfg, max_attempts=10)
    assert run == 0
    assert veiled == 10


def test_partial_drop_rate_veils_some(monkeypatch):
    # seed=0, rate=0.5 — deterministic split
    cfg = VeilConfig(enabled=True, drop_rate=0.5, seed=0)
    run, veiled = _run_loop(cfg, max_attempts=100)
    assert run + veiled == 100
    # With a fair coin we expect roughly 50/50; allow wide tolerance
    assert 20 <= veiled <= 80


def test_seeded_results_are_reproducible():
    cfg = VeilConfig(enabled=True, drop_rate=0.4, seed=13)
    r1, v1 = _run_loop(cfg, max_attempts=30)
    r2, v2 = _run_loop(cfg, max_attempts=30)
    assert r1 == r2
    assert v1 == v2


def test_veil_does_not_block_success_path():
    cfg = VeilConfig(enabled=True, drop_rate=0.0)
    run, veiled = _run_loop(cfg, max_attempts=5, always_fail=False)
    assert veiled == 0
    assert run == 1  # loop breaks on first success
