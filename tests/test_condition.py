"""Tests for retryctl.condition."""

import pytest
from retryctl.condition import (
    ConditionConfig,
    from_dict,
    should_abort_on_output,
    should_retry_on_output,
)


@pytest.fixture()
def empty_cfg() -> ConditionConfig:
    return ConditionConfig()


def test_from_dict_defaults():
    cfg = from_dict({})
    assert cfg.retry_on_stdout == []
    assert cfg.retry_on_stderr == []
    assert cfg.abort_on_stdout == []
    assert cfg.abort_on_stderr == []


def test_from_dict_full():
    cfg = from_dict(
        {
            "retry_on_stdout": ["transient"],
            "retry_on_stderr": ["timeout"],
            "abort_on_stdout": ["fatal"],
            "abort_on_stderr": ["permission denied"],
        }
    )
    assert cfg.retry_on_stdout == ["transient"]
    assert cfg.abort_on_stderr == ["permission denied"]


def test_no_patterns_never_retries_on_output(empty_cfg):
    assert should_retry_on_output(empty_cfg, "transient error", None) is False


def test_no_patterns_never_aborts_on_output(empty_cfg):
    assert should_abort_on_output(empty_cfg, "fatal", None) is False


def test_retry_on_stdout_matches():
    cfg = from_dict({"retry_on_stdout": ["retry me"]})
    assert should_retry_on_output(cfg, "please retry me now", None) is True


def test_retry_on_stdout_no_match():
    cfg = from_dict({"retry_on_stdout": ["retry me"]})
    assert should_retry_on_output(cfg, "all good", None) is False


def test_retry_on_stderr_matches():
    cfg = from_dict({"retry_on_stderr": ["timeout"]})
    assert should_retry_on_output(cfg, None, "connection timeout occurred") is True


def test_retry_on_stderr_no_match():
    cfg = from_dict({"retry_on_stderr": ["timeout"]})
    assert should_retry_on_output(cfg, None, "everything fine") is False


def test_abort_on_stdout_matches():
    cfg = from_dict({"abort_on_stdout": ["fatal"]})
    assert should_abort_on_output(cfg, "fatal error encountered", None) is True


def test_abort_on_stderr_matches():
    cfg = from_dict({"abort_on_stderr": ["permission denied"]})
    assert should_abort_on_output(cfg, None, "bash: permission denied") is True


def test_abort_on_stderr_no_match():
    cfg = from_dict({"abort_on_stderr": ["permission denied"]})
    assert should_abort_on_output(cfg, None, "just a warning") is False


def test_regex_pattern_used():
    cfg = from_dict({"retry_on_stderr": [r"error\s+\d+"]})
    assert should_retry_on_output(cfg, None, "error 503") is True
    assert should_retry_on_output(cfg, None, "error abc") is False


def test_none_output_does_not_crash():
    cfg = from_dict({"retry_on_stdout": ["oops"], "abort_on_stderr": ["fatal"]})
    assert should_retry_on_output(cfg, None, None) is False
    assert should_abort_on_output(cfg, None, None) is False


def test_multiple_patterns_any_match():
    cfg = from_dict({"retry_on_stdout": ["alpha", "beta", "gamma"]})
    assert should_retry_on_output(cfg, "beta hit", None) is True
    assert should_retry_on_output(cfg, "nothing here", None) is False
