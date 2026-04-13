"""Tests for retryctl.roster and retryctl.roster_middleware."""
from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from retryctl.roster import (
    RosterConfig,
    RosterEntry,
    _load_roster,
    _save_roster,
    list_entries,
    record_run,
)
from retryctl.roster_middleware import (
    describe_roster,
    on_run_complete,
    parse_roster,
    roster_config_to_dict,
)


# ---------------------------------------------------------------------------
# RosterConfig
# ---------------------------------------------------------------------------

def test_config_defaults():
    cfg = RosterConfig()
    assert cfg.enabled is False
    assert cfg.max_entries == 500
    assert "retryctl" in cfg.roster_file


def test_config_from_dict_full():
    cfg = RosterConfig.from_dict({"enabled": True, "max_entries": 10, "roster_file": "/tmp/r.json"})
    assert cfg.enabled is True
    assert cfg.max_entries == 10
    assert cfg.roster_file == "/tmp/r.json"


def test_config_from_dict_empty_uses_defaults():
    cfg = RosterConfig.from_dict({})
    assert cfg.enabled is False
    assert cfg.max_entries == 500


def test_config_from_dict_invalid_type_raises():
    with pytest.raises(TypeError):
        RosterConfig.from_dict("bad")


def test_config_zero_max_entries_raises():
    with pytest.raises(ValueError):
        RosterConfig.from_dict({"max_entries": 0})


# ---------------------------------------------------------------------------
# RosterEntry roundtrip
# ---------------------------------------------------------------------------

def test_entry_roundtrip():
    e = RosterEntry(command="echo hi", run_count=3, failure_count=1, last_seen=1000.0)
    assert RosterEntry.from_dict(e.to_dict()) == e


# ---------------------------------------------------------------------------
# record_run / list_entries
# ---------------------------------------------------------------------------

def test_record_run_disabled_does_nothing(tmp_path):
    cfg = RosterConfig(enabled=False, roster_file=str(tmp_path / "r.json"))
    record_run(cfg, "echo hi", succeeded=True)
    assert not (tmp_path / "r.json").exists()


def test_record_run_creates_entry(tmp_path):
    cfg = RosterConfig(enabled=True, roster_file=str(tmp_path / "r.json"))
    record_run(cfg, "echo hi", succeeded=True, now=1000.0)
    entries = list_entries(cfg)
    assert len(entries) == 1
    assert entries[0].command == "echo hi"
    assert entries[0].run_count == 1
    assert entries[0].failure_count == 0


def test_record_run_increments_failure(tmp_path):
    cfg = RosterConfig(enabled=True, roster_file=str(tmp_path / "r.json"))
    record_run(cfg, "false", succeeded=False, now=1000.0)
    record_run(cfg, "false", succeeded=False, now=1001.0)
    entries = list_entries(cfg)
    assert entries[0].failure_count == 2
    assert entries[0].run_count == 2


def test_record_run_respects_max_entries(tmp_path):
    cfg = RosterConfig(enabled=True, roster_file=str(tmp_path / "r.json"), max_entries=2)
    for i in range(5):
        record_run(cfg, f"cmd_{i}", succeeded=True, now=float(i))
    entries = list_entries(cfg)
    assert len(entries) <= 2


def test_list_entries_disabled_returns_empty(tmp_path):
    cfg = RosterConfig(enabled=False, roster_file=str(tmp_path / "r.json"))
    assert list_entries(cfg) == []


def test_load_roster_missing_file_returns_empty(tmp_path):
    result = _load_roster(str(tmp_path / "missing.json"))
    assert result == {}


# ---------------------------------------------------------------------------
# Middleware helpers
# ---------------------------------------------------------------------------

def test_parse_roster_empty_config():
    cfg = parse_roster({})
    assert cfg.enabled is False


def test_parse_roster_full_section():
    cfg = parse_roster({"roster": {"enabled": True, "max_entries": 20}})
    assert cfg.enabled is True
    assert cfg.max_entries == 20


def test_parse_roster_invalid_section_raises():
    with pytest.raises(TypeError):
        parse_roster({"roster": "bad"})


def test_roster_config_to_dict_roundtrip():
    cfg = RosterConfig(enabled=True, max_entries=99, roster_file="/x/y.json")
    d = roster_config_to_dict(cfg)
    assert d["enabled"] is True
    assert d["max_entries"] == 99
    assert d["roster_file"] == "/x/y.json"


def test_on_run_complete_records_entry(tmp_path):
    cfg = RosterConfig(enabled=True, roster_file=str(tmp_path / "r.json"))
    on_run_complete(cfg, "my-cmd", succeeded=False)
    entries = list_entries(cfg)
    assert entries[0].command == "my-cmd"
    assert entries[0].failure_count == 1


def test_describe_roster_disabled():
    cfg = RosterConfig(enabled=False)
    assert "disabled" in describe_roster(cfg)


def test_describe_roster_no_entries(tmp_path):
    cfg = RosterConfig(enabled=True, roster_file=str(tmp_path / "r.json"))
    assert "no entries" in describe_roster(cfg)


def test_describe_roster_shows_entries(tmp_path):
    cfg = RosterConfig(enabled=True, roster_file=str(tmp_path / "r.json"))
    record_run(cfg, "echo hello", succeeded=True)
    out = describe_roster(cfg)
    assert "echo hello" in out
    assert "runs=" in out
