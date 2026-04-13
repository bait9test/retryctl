"""Tests for retryctl/probe.py and retryctl/probe_middleware.py."""
from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from retryctl.probe import (
    ProbeConfig,
    ProbeSkip,
    check_probe,
    run_probe,
)
from retryctl.probe_middleware import (
    before_attempt,
    describe_probe,
    parse_probe,
    probe_config_to_dict,
)


# ---------------------------------------------------------------------------
# ProbeConfig.from_dict
# ---------------------------------------------------------------------------

def test_config_defaults():
    cfg = ProbeConfig()
    assert cfg.enabled is False
    assert cfg.command == []
    assert cfg.timeout == 5.0
    assert cfg.retries == 1
    assert cfg.skip_on_fail is True


def test_from_dict_empty_uses_defaults():
    cfg = ProbeConfig.from_dict({})
    assert cfg.enabled is False


def test_from_dict_full():
    cfg = ProbeConfig.from_dict({
        "enabled": True,
        "command": ["curl", "-sf", "http://localhost/health"],
        "timeout": 3.0,
        "retries": 2,
        "skip_on_fail": False,
    })
    assert cfg.enabled is True
    assert cfg.command == ["curl", "-sf", "http://localhost/health"]
    assert cfg.timeout == 3.0
    assert cfg.retries == 2
    assert cfg.skip_on_fail is False


def test_from_dict_string_command_splits():
    cfg = ProbeConfig.from_dict({"command": "curl -sf http://localhost/health"})
    assert cfg.command == ["curl", "-sf", "http://localhost/health"]
    assert cfg.enabled is True  # auto-enabled when command present


def test_from_dict_invalid_type_raises():
    with pytest.raises(TypeError):
        ProbeConfig.from_dict("not a dict")  # type: ignore


def test_from_dict_zero_timeout_raises():
    with pytest.raises(ValueError):
        ProbeConfig.from_dict({"command": ["true"], "timeout": 0})


def test_from_dict_zero_retries_raises():
    with pytest.raises(ValueError):
        ProbeConfig.from_dict({"command": ["true"], "retries": 0})


# ---------------------------------------------------------------------------
# run_probe
# ---------------------------------------------------------------------------

def _make_completed(returncode: int) -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=b"", stderr=b"")


def test_run_probe_disabled_returns_true():
    cfg = ProbeConfig(enabled=False, command=["false"])
    assert run_probe(cfg) is True


def test_run_probe_success_on_first_attempt():
    cfg = ProbeConfig(enabled=True, command=["true"], retries=3)
    with patch("subprocess.run", return_value=_make_completed(0)) as mock_run:
        result = run_probe(cfg)
    assert result is True
    assert mock_run.call_count == 1


def test_run_probe_fails_all_retries():
    cfg = ProbeConfig(enabled=True, command=["false"], retries=3)
    with patch("subprocess.run", return_value=_make_completed(1)):
        result = run_probe(cfg)
    assert result is False


def test_run_probe_succeeds_on_second_retry():
    cfg = ProbeConfig(enabled=True, command=["cmd"], retries=3)
    side_effects = [_make_completed(1), _make_completed(0)]
    with patch("subprocess.run", side_effect=side_effects) as mock_run:
        result = run_probe(cfg)
    assert result is True
    assert mock_run.call_count == 2


def test_run_probe_timeout_counts_as_failure():
    cfg = ProbeConfig(enabled=True, command=["slow"], retries=1, timeout=0.001)
    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="slow", timeout=0.001)):
        result = run_probe(cfg)
    assert result is False


def test_run_probe_oserror_counts_as_failure():
    cfg = ProbeConfig(enabled=True, command=["missing"], retries=1)
    with patch("subprocess.run", side_effect=OSError("not found")):
        result = run_probe(cfg)
    assert result is False


# ---------------------------------------------------------------------------
# check_probe / ProbeSkip
# ---------------------------------------------------------------------------

def test_check_probe_disabled_does_nothing():
    cfg = ProbeConfig(enabled=False)
    check_probe(cfg)  # should not raise


def test_check_probe_raises_probe_skip_when_skip_on_fail():
    cfg = ProbeConfig(enabled=True, command=["false"], retries=1, skip_on_fail=True)
    with patch("subprocess.run", return_value=_make_completed(1)):
        with pytest.raises(ProbeSkip):
            check_probe(cfg)


def test_check_probe_no_raise_when_skip_on_fail_false():
    cfg = ProbeConfig(enabled=True, command=["false"], retries=1, skip_on_fail=False)
    with patch("subprocess.run", return_value=_make_completed(1)):
        check_probe(cfg)  # should not raise


# ---------------------------------------------------------------------------
# middleware helpers
# ---------------------------------------------------------------------------

def test_parse_probe_empty_config():
    cfg = parse_probe({})
    assert cfg.enabled is False


def test_parse_probe_full_section():
    raw = {"probe": {"command": ["curl", "http://x"], "timeout": 2.0, "retries": 2}}
    cfg = parse_probe(raw)
    assert cfg.enabled is True
    assert cfg.timeout == 2.0


def test_parse_probe_invalid_section_type_raises():
    with pytest.raises(TypeError):
        parse_probe({"probe": "bad"})


def test_probe_config_to_dict_roundtrip():
    cfg = ProbeConfig(enabled=True, command=["ping"], timeout=3.0, retries=2, skip_on_fail=False)
    d = probe_config_to_dict(cfg)
    assert d["enabled"] is True
    assert d["command"] == ["ping"]
    assert d["timeout"] == 3.0
    assert d["retries"] == 2
    assert d["skip_on_fail"] is False


def test_before_attempt_calls_check_probe():
    cfg = ProbeConfig(enabled=True, command=["false"], retries=1, skip_on_fail=True)
    with patch("subprocess.run", return_value=_make_completed(1)):
        with pytest.raises(ProbeSkip):
            before_attempt(cfg)


def test_describe_probe_disabled():
    assert describe_probe(ProbeConfig()) == "probe: disabled"


def test_describe_probe_enabled():
    cfg = ProbeConfig(enabled=True, command=["curl", "http://x"], timeout=3.0, retries=2)
    desc = describe_probe(cfg)
    assert "enabled" in desc
    assert "curl" in desc
    assert "3.0" in desc
