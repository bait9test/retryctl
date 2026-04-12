"""Tests for retryctl.drain and retryctl.drain_middleware."""
from __future__ import annotations

import subprocess
import sys
from unittest.mock import MagicMock

import pytest

from retryctl.drain import DrainConfig, DrainResult, drain_process, _drain_stream
from retryctl.drain_middleware import (
    parse_drain,
    drain_config_to_dict,
    describe_drain,
    log_drain_result,
)


# ---------------------------------------------------------------------------
# DrainConfig
# ---------------------------------------------------------------------------

def test_config_defaults():
    cfg = DrainConfig()
    assert cfg.enabled is False
    assert cfg.max_lines == 0


def test_config_from_dict_full():
    cfg = DrainConfig.from_dict({"enabled": True, "max_lines": 50})
    assert cfg.enabled is True
    assert cfg.max_lines == 50


def test_config_from_dict_empty_uses_defaults():
    cfg = DrainConfig.from_dict({})
    assert cfg.enabled is False
    assert cfg.max_lines == 0


def test_config_from_dict_invalid_type_raises():
    with pytest.raises(TypeError):
        DrainConfig.from_dict("bad")


def test_config_negative_max_lines_raises():
    with pytest.raises(ValueError):
        DrainConfig.from_dict({"max_lines": -1})


# ---------------------------------------------------------------------------
# DrainResult
# ---------------------------------------------------------------------------

def test_drain_result_stdout_property():
    r = DrainResult(stdout_lines=["hello", "world"])
    assert r.stdout == "hello\nworld"


def test_drain_result_stderr_property():
    r = DrainResult(stderr_lines=["err"])
    assert r.stderr == "err"


# ---------------------------------------------------------------------------
# drain_process (integration with real subprocess)
# ---------------------------------------------------------------------------

def test_drain_process_disabled_returns_empty():
    cfg = DrainConfig(enabled=False)
    proc = MagicMock()
    result = drain_process(proc, cfg)
    assert result.stdout_lines == []
    assert result.stderr_lines == []


def test_drain_process_captures_stdout():
    cfg = DrainConfig(enabled=True)
    proc = subprocess.Popen(
        [sys.executable, "-c", "print('hello'); print('world')"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    result = drain_process(proc, cfg)
    proc.wait()
    assert "hello" in result.stdout_lines
    assert "world" in result.stdout_lines


def test_drain_process_respects_max_lines():
    cfg = DrainConfig(enabled=True, max_lines=2)
    proc = subprocess.Popen(
        [sys.executable, "-c", "for i in range(10): print(i)"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    result = drain_process(proc, cfg)
    proc.wait()
    assert len(result.stdout_lines) == 2


def test_drain_process_invokes_callback():
    seen = []
    cfg = DrainConfig(enabled=True, on_stdout=seen.append)
    proc = subprocess.Popen(
        [sys.executable, "-c", "print('ping')"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    drain_process(proc, cfg)
    proc.wait()
    assert "ping" in seen


# ---------------------------------------------------------------------------
# drain_middleware
# ---------------------------------------------------------------------------

def test_parse_drain_empty_config():
    cfg = parse_drain({})
    assert cfg.enabled is False


def test_parse_drain_full_section():
    cfg = parse_drain({"drain": {"enabled": True, "max_lines": 10}})
    assert cfg.enabled is True
    assert cfg.max_lines == 10


def test_parse_drain_invalid_section_type_raises():
    with pytest.raises(TypeError):
        parse_drain({"drain": "bad"})


def test_drain_config_to_dict_roundtrip():
    cfg = DrainConfig(enabled=True, max_lines=5)
    d = drain_config_to_dict(cfg)
    assert d == {"enabled": True, "max_lines": 5}


def test_describe_drain_disabled():
    assert describe_drain(DrainConfig()) == "drain: disabled"


def test_describe_drain_enabled_no_cap():
    assert describe_drain(DrainConfig(enabled=True)) == "drain: enabled"


def test_describe_drain_enabled_with_cap():
    result = describe_drain(DrainConfig(enabled=True, max_lines=20))
    assert "max_lines=20" in result


def test_log_drain_result_does_not_raise(caplog):
    result = DrainResult(stdout_lines=["out"], stderr_lines=["err"])
    import logging
    with caplog.at_level(logging.DEBUG, logger="retryctl.drain_middleware"):
        log_drain_result(result, attempt=1)
    assert any("out" in r.message for r in caplog.records)
    assert any("err" in r.message for r in caplog.records)
