"""Tests for retryctl.audit and retryctl.audit_hook."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from retryctl.audit import (
    AuditConfig,
    AuditEntry,
    _DEFAULT_AUDIT_FILE,
    build_audit_entry,
    write_audit_entry,
)
from retryctl.audit_hook import audit_on_finish
from retryctl.metrics import AttemptRecord, RunMetrics, record_attempt, finish


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _make_metrics(succeeded: bool = True, exit_code: int = 0) -> RunMetrics:
    m = RunMetrics()
    record_attempt(m, attempt=1, exit_code=exit_code, delay_before=0.0)
    finish(m, succeeded=succeeded)
    return m


# ---------------------------------------------------------------------------
# AuditConfig
# ---------------------------------------------------------------------------

def test_audit_config_defaults():
    cfg = AuditConfig()
    assert cfg.enabled is False
    assert cfg.audit_file == _DEFAULT_AUDIT_FILE


def test_audit_config_from_dict():
    cfg = AuditConfig.from_dict({"enabled": True, "audit_file": "/tmp/test.jsonl"})
    assert cfg.enabled is True
    assert cfg.audit_file == "/tmp/test.jsonl"


def test_audit_config_from_dict_empty():
    cfg = AuditConfig.from_dict({})
    assert cfg.enabled is False


# ---------------------------------------------------------------------------
# build_audit_entry
# ---------------------------------------------------------------------------

def test_build_audit_entry_succeeded():
    m = _make_metrics(succeeded=True, exit_code=0)
    entry = build_audit_entry("echo hi", m)
    assert entry.command == "echo hi"
    assert entry.succeeded is True
    assert entry.total_attempts == 1
    assert entry.exit_code == 0
    assert entry.elapsed_seconds >= 0.0


def test_build_audit_entry_failed():
    m = _make_metrics(succeeded=False, exit_code=1)
    entry = build_audit_entry("false", m)
    assert entry.succeeded is False
    assert entry.exit_code == 1


def test_build_audit_entry_no_attempts():
    m = RunMetrics()
    finish(m, succeeded=False)
    entry = build_audit_entry("cmd", m)
    assert entry.exit_code is None
    assert entry.elapsed_seconds >= 0.0


def test_audit_entry_to_dict_has_expected_keys():
    entry = AuditEntry(command="ls", succeeded=True, total_attempts=2, elapsed_seconds=1.5)
    d = entry.to_dict()
    assert set(d.keys()) == {"command", "succeeded", "total_attempts", "elapsed_seconds", "finished_at", "exit_code"}


# ---------------------------------------------------------------------------
# write_audit_entry
# ---------------------------------------------------------------------------

def test_write_audit_entry_disabled(tmp_path):
    cfg = AuditConfig(enabled=False, audit_file=str(tmp_path / "audit.jsonl"))
    entry = AuditEntry(command="x", succeeded=True, total_attempts=1, elapsed_seconds=0.1)
    write_audit_entry(entry, cfg)
    assert not (tmp_path / "audit.jsonl").exists()


def test_write_audit_entry_creates_file(tmp_path):
    path = tmp_path / "sub" / "audit.jsonl"
    cfg = AuditConfig(enabled=True, audit_file=str(path))
    entry = AuditEntry(command="ls", succeeded=True, total_attempts=1, elapsed_seconds=0.2)
    write_audit_entry(entry, cfg)
    assert path.exists()
    data = json.loads(path.read_text().strip())
    assert data["command"] == "ls"


def test_write_audit_entry_appends(tmp_path):
    path = tmp_path / "audit.jsonl"
    cfg = AuditConfig(enabled=True, audit_file=str(path))
    for i in range(3):
        entry = AuditEntry(command=f"cmd{i}", succeeded=True, total_attempts=1, elapsed_seconds=0.0)
        write_audit_entry(entry, cfg)
    lines = path.read_text().strip().splitlines()
    assert len(lines) == 3


def test_write_audit_entry_bad_path_logs_warning(caplog, tmp_path):
    cfg = AuditConfig(enabled=True, audit_file="/no/such/dir/audit.jsonl")
    entry = AuditEntry(command="x", succeeded=False, total_attempts=1, elapsed_seconds=0.0)
    import logging
    with caplog.at_level(logging.WARNING, logger="retryctl.audit"):
        write_audit_entry(entry, cfg)  # should not raise
    assert "audit" in caplog.text.lower()


# ---------------------------------------------------------------------------
# audit_hook
# ---------------------------------------------------------------------------

def test_audit_on_finish_disabled_skips(tmp_path):
    path = tmp_path / "audit.jsonl"
    cfg = AuditConfig(enabled=False, audit_file=str(path))
    m = _make_metrics()
    audit_on_finish("echo", m, cfg)
    assert not path.exists()


def test_audit_on_finish_writes_entry(tmp_path):
    path = tmp_path / "audit.jsonl"
    cfg = AuditConfig(enabled=True, audit_file=str(path))
    m = _make_metrics(succeeded=True, exit_code=0)
    audit_on_finish("echo hello", m, cfg)
    data = json.loads(path.read_text().strip())
    assert data["command"] == "echo hello"
    assert data["succeeded"] is True
