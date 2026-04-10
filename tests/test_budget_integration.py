"""Integration-style tests: budget interacting with middleware helpers end-to-end."""

from __future__ import annotations

import pytest

from retryctl.budget import BudgetConfig, BudgetTracker, BudgetExceeded
from retryctl.budget_middleware import enforce_budget_gate, on_retry_consumed


def _make_tracker(max_retries: int, window: float = 60.0) -> BudgetTracker:
    cfg = BudgetConfig(enabled=True, max_retries=max_retries, window_seconds=window)
    return BudgetTracker(cfg)


def test_full_retry_loop_exhausts_budget():
    """Simulates a retry loop consuming the full budget then being blocked."""
    tracker = _make_tracker(max_retries=3)
    allowed = 0
    for attempt in range(1, 10):
        try:
            enforce_budget_gate(tracker, attempt)
        except BudgetExceeded:
            break
        on_retry_consumed(tracker)
        allowed += 1
    assert allowed == 3


def test_budget_not_consumed_on_success():
    """If we never call on_retry_consumed, budget stays full."""
    tracker = _make_tracker(max_retries=2)
    # Pretend command succeeded on first try — no retries consumed
    assert tracker.remaining() == 2
    enforce_budget_gate(tracker, attempt=1)  # should not raise


def test_disabled_budget_never_raises():
    cfg = BudgetConfig()  # disabled
    tracker = BudgetTracker(cfg)
    for attempt in range(1, 50):
        enforce_budget_gate(tracker, attempt)  # must not raise
        on_retry_consumed(tracker)             # should be a no-op


def test_budget_exceeded_error_message():
    tracker = _make_tracker(max_retries=1)
    tracker.record_retry()
    with pytest.raises(BudgetExceeded) as exc_info:
        enforce_budget_gate(tracker, attempt=2)
    msg = str(exc_info.value)
    assert "budget exceeded" in msg.lower()
    assert "1/1" in msg


def test_key_in_exception():
    cfg = BudgetConfig(enabled=True, max_retries=1, window_seconds=60.0, key="my-service")
    tracker = BudgetTracker(cfg)
    tracker.record_retry()
    with pytest.raises(BudgetExceeded) as exc_info:
        tracker.check_or_raise()
    assert exc_info.value.key == "my-service"
    assert "my-service" in str(exc_info.value)
