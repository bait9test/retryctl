"""Tests for retryctl.verdict."""
import pytest
from retryctl.verdict import Verdict, VerdictCode, classify


# ---------------------------------------------------------------------------
# Verdict dataclass
# ---------------------------------------------------------------------------

def test_verdict_is_success_true():
    v = Verdict(code=VerdictCode.SUCCESS, attempts=1)
    assert v.is_success() is True


def test_verdict_is_success_false():
    v = Verdict(code=VerdictCode.EXHAUSTED, attempts=3)
    assert v.is_success() is False


def test_verdict_defaults():
    v = Verdict(code=VerdictCode.UNKNOWN)
    assert v.reason == ""
    assert v.exit_code is None
    assert v.attempts == 0
    assert v.extra == {}


# ---------------------------------------------------------------------------
# classify() — success
# ---------------------------------------------------------------------------

def test_classify_success():
    v = classify(succeeded=True, attempts=1, max_attempts=3, exit_code=0)
    assert v.code is VerdictCode.SUCCESS
    assert v.exit_code == 0
    assert v.attempts == 1
    assert v.is_success()


def test_classify_success_custom_reason():
    v = classify(succeeded=True, attempts=1, max_attempts=3, reason="all good")
    assert v.reason == "all good"


def test_classify_success_default_reason():
    v = classify(succeeded=True, attempts=1, max_attempts=3)
    assert "0" in v.reason


# ---------------------------------------------------------------------------
# classify() — exhausted
# ---------------------------------------------------------------------------

def test_classify_exhausted():
    v = classify(succeeded=False, attempts=3, max_attempts=3)
    assert v.code is VerdictCode.EXHAUSTED
    assert "3" in v.reason


def test_classify_exhausted_custom_reason():
    v = classify(succeeded=False, attempts=3, max_attempts=3, reason="gave up")
    assert v.reason == "gave up"


# ---------------------------------------------------------------------------
# classify() — aborted
# ---------------------------------------------------------------------------

def test_classify_aborted():
    v = classify(succeeded=False, attempts=1, max_attempts=5, aborted=True, exit_code=2)
    assert v.code is VerdictCode.ABORTED
    assert v.exit_code == 2


# ---------------------------------------------------------------------------
# classify() — timed out
# ---------------------------------------------------------------------------

def test_classify_timed_out():
    v = classify(succeeded=False, attempts=2, max_attempts=5, timed_out=True)
    assert v.code is VerdictCode.TIMED_OUT
    assert "deadline" in v.reason


# ---------------------------------------------------------------------------
# classify() — gate blocked
# ---------------------------------------------------------------------------

def test_classify_gate_blocked():
    v = classify(succeeded=False, attempts=0, max_attempts=3, gate_blocked=True)
    assert v.code is VerdictCode.GATE_BLOCKED


def test_classify_gate_blocked_takes_priority_over_timed_out():
    # gate_blocked checked before timed_out in priority order
    v = classify(
        succeeded=False, attempts=0, max_attempts=3,
        gate_blocked=True, timed_out=True,
    )
    assert v.code is VerdictCode.GATE_BLOCKED


# ---------------------------------------------------------------------------
# classify() — suppressed
# ---------------------------------------------------------------------------

def test_classify_suppressed():
    v = classify(succeeded=False, attempts=1, max_attempts=3, suppressed=True)
    assert v.code is VerdictCode.SUPPRESSED


# ---------------------------------------------------------------------------
# classify() — unknown fallback
# ---------------------------------------------------------------------------

def test_classify_unknown_when_no_flags_and_under_max():
    v = classify(succeeded=False, attempts=1, max_attempts=5)
    assert v.code is VerdictCode.UNKNOWN
