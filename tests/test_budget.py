"""Tests for retryctl.budget and retryctl.budget_middleware."""

from __future__ import annotations

import time
import pytest

from retryctl.budget import BudgetConfig, BudgetTracker, BudgetExceeded
from retryctl.budget_middleware import (
    parse_budget,
    budget_config_to_dict,
    enforce_budget_gate,
    on_retry_consumed,
)


# ---------------------------------------------------------------------------
# BudgetConfig
# ---------------------------------------------------------------------------

def test_config_defaults():
    cfg = BudgetConfig()
    assert cfg.enabled is False
    assert cfg.max_retries == 0
    assert cfg.window_seconds == 60.0
    assert cfg.key == "default"


def test_config_from_dict_full():
    cfg = BudgetConfig.from_dict({"max_retries": 5, "window_seconds": 30.0, "key": "svc"})
    assert cfg.enabled is True
    assert cfg.max_retries == 5
    assert cfg.window_seconds == 30.0
    assert cfg.key == "svc"


def test_config_from_dict_empty():
    cfg = BudgetConfig.from_dict({})
    assert cfg.enabled is False
    assert cfg.max_retries == 0


def test_config_zero_window_raises():
    with pytest.raises(ValueError, match="window_seconds must be positive"):
        BudgetConfig.from_dict({"max_retries": 3, "window_seconds": 0})


# ---------------------------------------------------------------------------
# BudgetTracker — disabled
# ---------------------------------------------------------------------------

def test_disabled_tracker_always_allows():
    tracker = BudgetTracker(BudgetConfig())
    for _ in range(20):
        assert tracker.is_allowed() is True


def test_disabled_remaining_returns_minus_one():
    tracker = BudgetTracker(BudgetConfig())
    assert tracker.remaining() == -1


# ---------------------------------------------------------------------------
# BudgetTracker — enabled
# ---------------------------------------------------------------------------

def test_allows_up_to_max():
    cfg = BudgetConfig(enabled=True, max_retries=3, window_seconds=60.0)
    tracker = BudgetTracker(cfg)
    for _ in range(3):
        assert tracker.is_allowed()
        tracker.record_retry()
    assert tracker.is_allowed() is False


def test_check_or_raise_raises_when_exhausted():
    cfg = BudgetConfig(enabled=True, max_retries=2, window_seconds=60.0)
    tracker = BudgetTracker(cfg)
    tracker.record_retry()
    tracker.record_retry()
    with pytest.raises(BudgetExceeded) as exc_info:
        tracker.check_or_raise()
    assert exc_info.value.used == 2
    assert exc_info.value.limit == 2


def test_evicts_expired_timestamps(monkeypatch):
    cfg = BudgetConfig(enabled=True, max_retries=2, window_seconds=5.0)
    tracker = BudgetTracker(cfg)
    # Inject old timestamps directly
    old_time = time.monotonic() - 10.0
    tracker._timestamps = [old_time, old_time]
    # After eviction both should be gone
    assert tracker.is_allowed() is True
    assert tracker.remaining() == 2


def test_remaining_decrements():
    cfg = BudgetConfig(enabled=True, max_retries=4, window_seconds=60.0)
    tracker = BudgetTracker(cfg)
    assert tracker.remaining() == 4
    tracker.record_retry()
    assert tracker.remaining() == 3


# ---------------------------------------------------------------------------
# Middleware helpers
# ---------------------------------------------------------------------------

def test_parse_budget_reads_section():
    raw = {"budget": {"max_retries": 10, "window_seconds": 120.0}}
    cfg = parse_budget(raw)
    assert cfg.max_retries == 10


def test_parse_budget_missing_section_uses_defaults():
    cfg = parse_budget({})
    assert cfg.enabled is False


def test_parse_budget_invalid_type_raises():
    with pytest.raises(TypeError):
        parse_budget({"budget": "bad"})


def test_budget_config_to_dict_roundtrip():
    cfg = BudgetConfig(enabled=True, max_retries=7, window_seconds=45.0, key="x")
    d = budget_config_to_dict(cfg)
    cfg2 = BudgetConfig.from_dict(d)
    assert cfg2.max_retries == cfg.max_retries
    assert cfg2.window_seconds == cfg.window_seconds


def test_enforce_budget_gate_raises_when_exhausted():
    cfg = BudgetConfig(enabled=True, max_retries=1, window_seconds=60.0)
    tracker = BudgetTracker(cfg)
    tracker.record_retry()
    with pytest.raises(BudgetExceeded):
        enforce_budget_gate(tracker, attempt=2)


def test_on_retry_consumed_records_and_logs(caplog):
    import logging
    cfg = BudgetConfig(enabled=True, max_retries=5, window_seconds=60.0)
    tracker = BudgetTracker(cfg)
    with caplog.at_level(logging.DEBUG, logger="retryctl.budget_middleware"):
        on_retry_consumed(tracker)
    assert tracker.remaining() == 4
