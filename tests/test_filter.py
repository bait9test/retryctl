"""Tests for retryctl.filter."""

import pytest
from retryctl.filter import FilterConfig, is_retryable, should_abort


@pytest.fixture()
def default_cfg() -> FilterConfig:
    return FilterConfig()


# ---------------------------------------------------------------------------
# is_retryable – basic cases
# ---------------------------------------------------------------------------

def test_exit_zero_never_retried(default_cfg):
    assert is_retryable(0, "", default_cfg) is False


def test_nonzero_retried_by_default(default_cfg):
    assert is_retryable(1, "", default_cfg) is True


def test_nonzero_retried_with_stderr(default_cfg):
    assert is_retryable(2, "connection refused", default_cfg) is True


# ---------------------------------------------------------------------------
# fatal exit codes
# ---------------------------------------------------------------------------

def test_fatal_exit_code_not_retried():
    cfg = FilterConfig(fatal_exit_codes=[1, 2])
    assert is_retryable(1, "", cfg) is False
    assert is_retryable(2, "some error", cfg) is False


def test_non_fatal_exit_code_still_retried():
    cfg = FilterConfig(fatal_exit_codes=[1])
    assert is_retryable(3, "", cfg) is True


# ---------------------------------------------------------------------------
# retryable_exit_codes whitelist
# ---------------------------------------------------------------------------

def test_exit_code_not_in_whitelist_not_retried():
    cfg = FilterConfig(retryable_exit_codes=[1, 2])
    assert is_retryable(3, "", cfg) is False


def test_exit_code_in_whitelist_retried():
    cfg = FilterConfig(retryable_exit_codes=[1, 2])
    assert is_retryable(2, "", cfg) is True


# ---------------------------------------------------------------------------
# retryable_stderr_patterns
# ---------------------------------------------------------------------------

def test_stderr_pattern_match_retried():
    cfg = FilterConfig(retryable_stderr_patterns=[r"timeout", r"refused"])
    assert is_retryable(1, "connection timeout occurred", cfg) is True


def test_stderr_pattern_no_match_not_retried():
    cfg = FilterConfig(retryable_stderr_patterns=[r"timeout"])
    assert is_retryable(1, "permission denied", cfg) is False


def test_stderr_pattern_partial_match_is_enough():
    cfg = FilterConfig(retryable_stderr_patterns=[r"err\d+"])
    assert is_retryable(1, "got err42 from server", cfg) is True


# ---------------------------------------------------------------------------
# combined rules
# ---------------------------------------------------------------------------

def test_fatal_takes_priority_over_whitelist():
    cfg = FilterConfig(retryable_exit_codes=[1], fatal_exit_codes=[1])
    assert is_retryable(1, "", cfg) is False


def test_whitelist_and_pattern_both_must_pass():
    cfg = FilterConfig(retryable_exit_codes=[1], retryable_stderr_patterns=[r"retry"])
    # exit code matches but pattern does not
    assert is_retryable(1, "hard failure", cfg) is False
    # both match
    assert is_retryable(1, "please retry later", cfg) is True


# ---------------------------------------------------------------------------
# should_abort
# ---------------------------------------------------------------------------

def test_should_abort_true_for_fatal():
    cfg = FilterConfig(fatal_exit_codes=[137])
    assert should_abort(137, cfg) is True


def test_should_abort_false_for_non_fatal():
    cfg = FilterConfig(fatal_exit_codes=[137])
    assert should_abort(1, cfg) is False


def test_should_abort_empty_fatal_list(default_cfg):
    assert should_abort(1, default_cfg) is False
