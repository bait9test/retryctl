"""Tests for retryctl.ratelimit."""

from __future__ import annotations

import time
import pytest
from unittest.mock import patch

from retryctl.ratelimit import RateLimitConfig, RateLimiter


# ---------------------------------------------------------------------------
# RateLimitConfig
# ---------------------------------------------------------------------------

def test_config_disabled_by_default():
    cfg = RateLimitConfig()
    assert not cfg.enabled


def test_config_enabled_when_max_set():
    cfg = RateLimitConfig(max_attempts_per_window=5)
    assert cfg.enabled


# ---------------------------------------------------------------------------
# RateLimiter.is_allowed / record
# ---------------------------------------------------------------------------

def test_disabled_limiter_always_allows():
    limiter = RateLimiter(RateLimitConfig())
    for _ in range(100):
        assert limiter.is_allowed()


def test_allows_up_to_max():
    cfg = RateLimitConfig(max_attempts_per_window=3, window_seconds=60.0)
    limiter = RateLimiter(cfg)
    now = 1000.0
    for _ in range(3):
        assert limiter.is_allowed(now)
        limiter.record(now)
    assert not limiter.is_allowed(now)


def test_evicts_expired_timestamps():
    cfg = RateLimitConfig(max_attempts_per_window=2, window_seconds=10.0)
    limiter = RateLimiter(cfg)
    limiter.record(now=0.0)
    limiter.record(now=1.0)
    # Both slots used at t=5 (within window)
    assert not limiter.is_allowed(now=5.0)
    # At t=11, the t=0 entry is expired; one slot free
    assert limiter.is_allowed(now=11.0)
    # At t=12, both entries expired
    assert limiter.is_allowed(now=12.0)


def test_record_uses_monotonic_when_now_is_none():
    cfg = RateLimitConfig(max_attempts_per_window=1, window_seconds=60.0)
    limiter = RateLimiter(cfg)
    before = time.monotonic()
    limiter.record()
    after = time.monotonic()
    ts = limiter._timestamps[-1]
    assert before <= ts <= after


# ---------------------------------------------------------------------------
# RateLimiter.wait_until_allowed
# ---------------------------------------------------------------------------

def test_wait_records_attempt_when_immediately_allowed():
    cfg = RateLimitConfig(max_attempts_per_window=3, window_seconds=60.0)
    limiter = RateLimiter(cfg)
    limiter.wait_until_allowed()
    assert len(limiter._timestamps) == 1


def test_wait_disabled_does_not_record():
    limiter = RateLimiter(RateLimitConfig())
    limiter.wait_until_allowed()
    assert len(limiter._timestamps) == 0


def test_wait_sleeps_until_window_clears():
    cfg = RateLimitConfig(max_attempts_per_window=1, window_seconds=5.0)
    limiter = RateLimiter(cfg)

    sleep_calls: list[float] = []

    # Pre-fill the window at a fixed monotonic reference
    base = 1000.0
    limiter.record(now=base)

    with patch("retryctl.ratelimit.time.monotonic") as mock_mono, \
         patch("retryctl.ratelimit.time.sleep", side_effect=lambda s: sleep_calls.append(s)) as _:
        # First call: still inside window → sleep needed
        # Second call: window has cleared
        mock_mono.side_effect = [base + 2.0, base + 5.1]
        limiter.wait_until_allowed()

    assert len(sleep_calls) == 1
    assert sleep_calls[0] == pytest.approx(base + 5.0 - (base + 2.0), abs=0.01)
