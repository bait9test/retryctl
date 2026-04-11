"""Tests for retryctl.trace and retryctl.trace_middleware."""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from retryctl.trace import (
    TraceConfig,
    TraceContext,
    inject_trace_env,
    new_trace,
    write_trace_record,
)
from retryctl.trace_middleware import (
    finalise_trace,
    parse_trace,
    setup_trace,
    trace_config_to_dict,
)


# ---------------------------------------------------------------------------
# TraceConfig
# ---------------------------------------------------------------------------

def test_config_defaults():
    cfg = TraceConfig()
    assert cfg.enabled is False
    assert cfg.trace_id is None
    assert cfg.output_file is None
    assert cfg.env_prefix == "RETRYCTL"


def test_config_from_dict_full():
    cfg = TraceConfig.from_dict({
        "enabled": True,
        "trace_id": "abc-123",
        "output_file": "/tmp/trace.jsonl",
        "env_prefix": "APP",
    })
    assert cfg.enabled is True
    assert cfg.trace_id == "abc-123"
    assert cfg.output_file == "/tmp/trace.jsonl"
    assert cfg.env_prefix == "APP"


def test_config_from_dict_empty():
    cfg = TraceConfig.from_dict({})
    assert cfg.enabled is False


def test_config_from_dict_invalid_type_raises():
    with pytest.raises(TypeError):
        TraceConfig.from_dict("not-a-dict")  # type: ignore


# ---------------------------------------------------------------------------
# TraceContext
# ---------------------------------------------------------------------------

def test_new_trace_generates_ids():
    cfg = TraceConfig(enabled=True)
    ctx = new_trace(cfg)
    assert ctx.trace_id
    assert ctx.span_id
    assert ctx.trace_id != ctx.span_id


def test_new_trace_reuses_configured_trace_id():
    cfg = TraceConfig(enabled=True, trace_id="fixed-id")
    ctx = new_trace(cfg)
    assert ctx.trace_id == "fixed-id"


def test_to_env_default_prefix():
    ctx = TraceContext(trace_id="t1", span_id="s1")
    env = ctx.to_env()
    assert env["RETRYCTL_TRACE_ID"] == "t1"
    assert env["RETRYCTL_SPAN_ID"] == "s1"


def test_to_env_custom_prefix():
    ctx = TraceContext(trace_id="t1", span_id="s1")
    env = ctx.to_env(prefix="MYAPP")
    assert "MYAPP_TRACE_ID" in env


def test_inject_trace_env_merges():
    cfg = TraceConfig(enabled=True, env_prefix="X")
    ctx = TraceContext(trace_id="tid", span_id="sid")
    base = {"EXISTING": "val"}
    merged = inject_trace_env(cfg, ctx, base)
    assert merged["EXISTING"] == "val"
    assert merged["X_TRACE_ID"] == "tid"


# ---------------------------------------------------------------------------
# write_trace_record
# ---------------------------------------------------------------------------

def test_write_trace_record(tmp_path):
    ctx = TraceContext(trace_id="t", span_id="s")
    dest = tmp_path / "trace.jsonl"
    write_trace_record(ctx, str(dest))
    lines = dest.read_text().splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["trace_id"] == "t"
    assert record["span_id"] == "s"


def test_write_trace_record_appends(tmp_path):
    ctx = TraceContext(trace_id="t", span_id="s")
    dest = tmp_path / "trace.jsonl"
    write_trace_record(ctx, str(dest))
    write_trace_record(ctx, str(dest))
    assert len(dest.read_text().splitlines()) == 2


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

def test_parse_trace_empty_config():
    cfg = parse_trace({})
    assert isinstance(cfg, TraceConfig)
    assert cfg.enabled is False


def test_parse_trace_full_section():
    cfg = parse_trace({"trace": {"enabled": True, "env_prefix": "T"}})
    assert cfg.enabled is True
    assert cfg.env_prefix == "T"


def test_parse_trace_invalid_section_raises():
    with pytest.raises(TypeError):
        parse_trace({"trace": "bad"})


def test_trace_config_to_dict_roundtrip():
    cfg = TraceConfig(enabled=True, trace_id="x", output_file="/f", env_prefix="P")
    d = trace_config_to_dict(cfg)
    cfg2 = TraceConfig.from_dict(d)
    assert cfg2.enabled == cfg.enabled
    assert cfg2.env_prefix == cfg.env_prefix


def test_setup_trace_disabled_returns_none():
    cfg = TraceConfig(enabled=False)
    ctx, env = setup_trace(cfg, base_env={"A": "1"})
    assert ctx is None
    assert env["A"] == "1"


def test_setup_trace_enabled_injects_env():
    cfg = TraceConfig(enabled=True, env_prefix="R")
    ctx, env = setup_trace(cfg)
    assert ctx is not None
    assert "R_TRACE_ID" in env
    assert "R_SPAN_ID" in env


def test_finalise_trace_disabled_does_nothing(tmp_path):
    cfg = TraceConfig(enabled=False, output_file=str(tmp_path / "out.jsonl"))
    finalise_trace(cfg, None)
    assert not (tmp_path / "out.jsonl").exists()


def test_finalise_trace_writes_file(tmp_path):
    cfg = TraceConfig(enabled=True, output_file=str(tmp_path / "out.jsonl"))
    ctx = TraceContext(trace_id="t", span_id="s")
    finalise_trace(cfg, ctx)
    assert (tmp_path / "out.jsonl").exists()
