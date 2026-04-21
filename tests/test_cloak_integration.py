"""Integration-style tests: run a simulated retry loop with cloak active."""
from __future__ import annotations

from retryctl.cloak import CloakConfig, CloakTracker, CloakedAttempt
from retryctl.cloak_middleware import before_attempt


def _run_loop(
    cfg: CloakConfig,
    total_attempts: int,
) -> tuple[list[int], list[int]]:
    """Returns (executed_attempts, cloaked_attempts)."""
    tracker = CloakTracker(cfg)
    executed: list[int] = []
    cloaked: list[int] = []
    for i in range(1, total_attempts + 1):
        try:
            before_attempt(tracker, i)
            executed.append(i)
        except CloakedAttempt as e:
            cloaked.append(e.attempt)
    return executed, cloaked


def test_disabled_cloak_runs_all_attempts():
    cfg = CloakConfig(enabled=False, mask_rate=1.0, seed=0)
    executed, cloaked = _run_loop(cfg, 10)
    assert len(executed) == 10
    assert cloaked == []


def test_full_mask_rate_cloaks_all():
    cfg = CloakConfig(enabled=True, mask_rate=1.0, seed=0)
    executed, cloaked = _run_loop(cfg, 8)
    assert executed == []
    assert len(cloaked) == 8


def test_zero_mask_rate_cloaks_none():
    cfg = CloakConfig(enabled=True, mask_rate=0.0, seed=0)
    executed, cloaked = _run_loop(cfg, 8)
    assert len(executed) == 8
    assert cloaked == []


def test_partial_rate_splits_attempts():
    cfg = CloakConfig(enabled=True, mask_rate=0.5, seed=42)
    executed, cloaked = _run_loop(cfg, 100)
    # With 50 % rate and 100 attempts we expect roughly half each; allow ±20
    assert 20 < len(cloaked) < 80
    assert len(executed) + len(cloaked) == 100


def test_seeded_run_is_deterministic():
    cfg = CloakConfig(enabled=True, mask_rate=0.4, seed=13)
    _, cloaked1 = _run_loop(cfg, 50)
    _, cloaked2 = _run_loop(cfg, 50)
    assert cloaked1 == cloaked2
