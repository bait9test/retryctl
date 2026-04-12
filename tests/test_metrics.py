"""Tests for retryctl.metrics."""

import time

import pytest

from retryctl.metrics import AttemptRecord, RunMetrics


# ---------------------------------------------------------------------------
# AttemptRecord
# ---------------------------------------------------------------------------

def test_attempt_record_stores_fields():
    rec = AttemptRecord(attempt=1, exit_code=1, duration_seconds=0.5, delay_before_next=2.0)
    assert rec.attempt == 1
    assert rec.exit_code == 1
    assert rec.duration_seconds == 0.5
    assert rec.delay_before_next == 2.0


def test_attempt_record_no_delay():
    rec = AttemptRecord(attempt=3, exit_code=0, duration_seconds=0.1)
    assert rec.delay_before_next is None


# ---------------------------------------------------------------------------
# RunMetrics.record_attempt / total_attempts
# ---------------------------------------------------------------------------

def test_record_attempt_increments_count():
    m = RunMetrics(command="echo hi")
    m.record_attempt(1, exit_code=1, duration_seconds=0.1, delay_before_next=1.0)
    m.record_attempt(2, exit_code=0, duration_seconds=0.2)
    assert m.total_attempts == 2


def test_record_attempt_preserves_order():
    m = RunMetrics(command="false")
    m.record_attempt(1, exit_code=1, duration_seconds=0.1, delay_before_next=2.0)
    m.record_attempt(2, exit_code=1, duration_seconds=0.1, delay_before_next=4.0)
    m.record_attempt(3, exit_code=0, duration_seconds=0.1)
    assert [r.attempt for r in m.attempts] == [1, 2, 3]


# ---------------------------------------------------------------------------
# RunMetrics.finish
# ---------------------------------------------------------------------------

def test_finish_sets_succeeded_and_timestamp():
    m = RunMetrics(command="ls")
    assert m.finished_at is None
    m.finish(succeeded=True)
    assert m.succeeded is True
    assert m.finished_at is not None


def test_finish_failure():
    m = RunMetrics(command="false")
    m.finish(succeeded=False)
    assert m.succeeded is False


def test_finish_timestamp_is_recent():
    """finished_at should be set to approximately the current time."""
    before = time.time()
    m = RunMetrics(command="ls")
    m.finish(succeeded=True)
    after = time.time()
    assert before <= m.finished_at <= after


# ---------------------------------------------------------------------------
# RunMetrics.total_delay_seconds
# ---------------------------------------------------------------------------

def test_total_delay_sums_delays():
    m = RunMetrics(command="cmd")
    m.record_attempt(1, exit_code=1, duration_seconds=0.1, delay_before_next=1.5)
    m.record_attempt(2, exit_code=1, duration_seconds=0.1, delay_before_next=3.0)
    m.record_attempt(3, exit_code=0, duration_seconds=0.1)
    assert m.total_delay_seconds == pytest.approx(4.5)


def test_total_delay_zero_when_no_delays():
    m = RunMetrics(command="cmd")
    m.record_attempt(1, exit_code=0, duration_seconds=0.2)
    assert m.total_delay_seconds == 0.0


# ---------------------------------------------------------------------------
# RunMetrics.summary
# ---------------------------------------------------------------------------

def test_summary_structure():
    m = RunMetrics(co