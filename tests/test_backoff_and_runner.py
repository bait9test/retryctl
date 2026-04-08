"""Tests for backoff strategies and the retry runner."""

import subprocess
from unittest.mock import MagicMock, call, patch

import pytest

from retryctl.backoff import BackoffConfig, BackoffStrategy, compute_delay, delay_sequence
from retryctl.runner import run_with_retry


# --- backoff tests ---

def test_fixed_delay_no_jitter():
    cfg = BackoffConfig(strategy=BackoffStrategy.FIXED, base_delay=5.0, jitter=False)
    assert compute_delay(0, cfg) == 5.0
    assert compute_delay(10, cfg) == 5.0


def test_linear_delay_no_jitter():
    cfg = BackoffConfig(strategy=BackoffStrategy.LINEAR, base_delay=2.0, jitter=False)
    assert compute_delay(0, cfg) == 2.0
    assert compute_delay(2, cfg) == 6.0


def test_exponential_delay_no_jitter():
    cfg = BackoffConfig(
        strategy=BackoffStrategy.EXPONENTIAL, base_delay=1.0, multiplier=2.0, jitter=False
    )
    assert compute_delay(0, cfg) == 1.0
    assert compute_delay(3, cfg) == 8.0


def test_max_delay_cap():
    cfg = BackoffConfig(
        strategy=BackoffStrategy.EXPONENTIAL,
        base_delay=1.0,
        multiplier=2.0,
        max_delay=10.0,
        jitter=False,
    )
    assert compute_delay(10, cfg) == 10.0


def test_jitter_within_range():
    cfg = BackoffConfig(strategy=BackoffStrategy.FIXED, base_delay=10.0, jitter=True)
    for _ in range(50):
        d = compute_delay(0, cfg)
        assert 0 <= d <= 10.0


def test_delay_sequence_yields_increasing_values():
    cfg = BackoffConfig(strategy=BackoffStrategy.EXPONENTIAL, base_delay=1.0, jitter=False)
    seq = delay_sequence(cfg)
    values = [next(seq) for _ in range(5)]
    assert values == sorted(values)


# --- runner tests ---

@patch("retryctl.runner.time.sleep")
@patch("retryctl.runner.subprocess.run")
def test_succeeds_on_first_attempt(mock_run, mock_sleep):
    mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")
    result = run_with_retry(["echo", "hi"], max_attempts=3)
    assert result.succeeded
    assert result.attempts == 1
    mock_sleep.assert_not_called()


@patch("retryctl.runner.time.sleep")
@patch("retryctl.runner.subprocess.run")
def test_retries_on_failure_then_succeeds(mock_run, mock_sleep):
    mock_run.side_effect = [
        MagicMock(returncode=1, stdout="", stderr="err"),
        MagicMock(returncode=0, stdout="done", stderr=""),
    ]
    cfg = BackoffConfig(strategy=BackoffStrategy.FIXED, base_delay=0.0, jitter=False)
    result = run_with_retry(["false"], max_attempts=3, backoff=cfg)
    assert result.succeeded
    assert result.attempts == 2
    assert mock_sleep.call_count == 1


@patch("retryctl.runner.time.sleep")
@patch("retryctl.runner.subprocess.run")
def test_exhausts_all_attempts(mock_run, mock_sleep):
    mock_run.return_value = MagicMock(returncode=2, stdout="", stderr="bad")
    cfg = BackoffConfig(strategy=BackoffStrategy.FIXED, base_delay=0.0, jitter=False)
    result = run_with_retry(["false"], max_attempts=4, backoff=cfg)
    assert not result.succeeded
    assert result.attempts == 4
    assert mock_sleep.call_count == 3
