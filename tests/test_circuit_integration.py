"""Integration-style tests: circuit breaker wired through the middleware layer."""
from __future__ import annotations

import pytest

from retryctl.circuit import CircuitConfig, CircuitOpen
from retryctl.circuit_middleware import (
    enforce_circuit_gate,
    on_attempt_failure,
    on_run_success,
)


@pytest.fixture()
def cfg(tmp_path) -> CircuitConfig:
    return CircuitConfig(
        enabled=True,
        failure_threshold=2,
        reset_seconds=120,
        state_dir=str(tmp_path),
    )


def _simulate_attempts(cfg: CircuitConfig, key: str, count: int) -> int:
    """Run *count* failing attempts; return how many passed the gate."""
    passed = 0
    for _ in range(count):
        try:
            enforce_circuit_gate(cfg, key)
        except CircuitOpen:
            break
        on_attempt_failure(cfg, key)
        passed += 1
    return passed


def test_exactly_threshold_attempts_pass(cfg):
    passed = _simulate_attempts(cfg, "job", 10)
    assert passed == cfg.failure_threshold


def test_second_key_unaffected(cfg):
    _simulate_attempts(cfg, "job-a", 10)
    # job-b should still be open (not tripped)
    enforce_circuit_gate(cfg, "job-b")  # must not raise


def test_success_between_failures_resets_counter(cfg):
    on_attempt_failure(cfg, "job")  # 1 failure
    on_run_success(cfg, "job")  # reset
    on_attempt_failure(cfg, "job")  # 1 failure again
    enforce_circuit_gate(cfg, "job")  # still below threshold → must not raise


def test_disabled_config_never_trips(tmp_path):
    cfg = CircuitConfig(
        enabled=False, failure_threshold=1, reset_seconds=120, state_dir=str(tmp_path)
    )
    for _ in range(5):
        on_attempt_failure(cfg, "job")
    enforce_circuit_gate(cfg, "job")  # must not raise


def test_circuit_open_exception_carries_key(cfg):
    for _ in range(cfg.failure_threshold):
        on_attempt_failure(cfg, "my-job")
    with pytest.raises(CircuitOpen) as exc_info:
        enforce_circuit_gate(cfg, "my-job")
    assert exc_info.value.key == "my-job"
    assert exc_info.value.opens_until > 0
