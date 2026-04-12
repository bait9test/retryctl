"""Tests for retryctl.snapshot and retryctl.snapshot_middleware."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from retryctl.snapshot import (
    SnapshotConfig,
    SnapshotEntry,
    _hash,
    compare_snapshots,
    load_snapshots,
    save_snapshots,
    take_snapshot,
)
from retryctl.snapshot_middleware import (
    describe_snapshot,
    on_attempt_complete,
    parse_snapshot,
    snapshot_config_to_dict,
)


# ---------------------------------------------------------------------------
# SnapshotConfig
# ---------------------------------------------------------------------------

def test_config_defaults():
    cfg = SnapshotConfig()
    assert cfg.enabled is False
    assert cfg.compare_stdout is True
    assert cfg.compare_stderr is False
    assert cfg.fail_on_change is False


def test_config_from_dict_full():
    cfg = SnapshotConfig.from_dict({
        "enabled": True,
        "path": "/tmp/snaps",
        "compare_stdout": False,
        "compare_stderr": True,
        "fail_on_change": True,
    })
    assert cfg.enabled is True
    assert cfg.path == "/tmp/snaps"
    assert cfg.compare_stdout is False
    assert cfg.compare_stderr is True
    assert cfg.fail_on_change is True


def test_config_from_dict_empty_uses_defaults():
    cfg = SnapshotConfig.from_dict({})
    assert cfg.enabled is False


def test_config_from_dict_invalid_type_raises():
    with pytest.raises(TypeError):
        SnapshotConfig.from_dict("bad")


# ---------------------------------------------------------------------------
# _hash helper
# ---------------------------------------------------------------------------

def test_hash_none_returns_none():
    assert _hash(None) is None


def test_hash_returns_16_char_hex():
    h = _hash("hello")
    assert isinstance(h, str)
    assert len(h) == 16


def test_hash_same_input_same_output():
    assert _hash("abc") == _hash("abc")


def test_hash_different_inputs_differ():
    assert _hash("abc") != _hash("xyz")


# ---------------------------------------------------------------------------
# take_snapshot / compare_snapshots
# ---------------------------------------------------------------------------

def test_take_snapshot_hashes_stdout():
    cfg = SnapshotConfig(enabled=True)
    e = take_snapshot(cfg, 1, "out", "err")
    assert e.stdout_hash is not None
    assert e.stderr_hash is None  # compare_stderr=False by default


def test_take_snapshot_skips_stdout_when_disabled():
    cfg = SnapshotConfig(enabled=True, compare_stdout=False, compare_stderr=True)
    e = take_snapshot(cfg, 1, "out", "err")
    assert e.stdout_hash is None
    assert e.stderr_hash is not None


def test_compare_snapshots_detects_change():
    a = SnapshotEntry(attempt=1, stdout_hash="aaa", stderr_hash=None)
    b = SnapshotEntry(attempt=2, stdout_hash="bbb", stderr_hash=None)
    assert compare_snapshots(a, b) is True


def test_compare_snapshots_no_change():
    a = SnapshotEntry(attempt=1, stdout_hash="aaa", stderr_hash=None)
    b = SnapshotEntry(attempt=2, stdout_hash="aaa", stderr_hash=None)
    assert compare_snapshots(a, b) is False


# ---------------------------------------------------------------------------
# save / load
# ---------------------------------------------------------------------------

def test_save_and_load_roundtrip(tmp_path):
    cfg = SnapshotConfig(enabled=True, path=str(tmp_path))
    entries = [
        SnapshotEntry(attempt=1, stdout_hash="abc", stderr_hash=None),
        SnapshotEntry(attempt=2, stdout_hash="def", stderr_hash=None, changed=True),
    ]
    save_snapshots(cfg, "my cmd", entries)
    loaded = load_snapshots(cfg, "my cmd")
    assert len(loaded) == 2
    assert loaded[1].changed is True


def test_load_missing_returns_empty(tmp_path):
    cfg = SnapshotConfig(enabled=True, path=str(tmp_path))
    assert load_snapshots(cfg, "nonexistent") == []


# ---------------------------------------------------------------------------
# middleware
# ---------------------------------------------------------------------------

def test_on_attempt_complete_disabled_noop():
    cfg = SnapshotConfig(enabled=False)
    changed, hist = on_attempt_complete(cfg, "cmd", 1, "out", "err", [])
    assert changed is False
    assert hist == []


def test_on_attempt_complete_first_attempt_not_changed(tmp_path):
    cfg = SnapshotConfig(enabled=True, path=str(tmp_path))
    changed, hist = on_attempt_complete(cfg, "cmd", 1, "out", "err", [])
    assert changed is False
    assert len(hist) == 1


def test_on_attempt_complete_detects_change(tmp_path):
    cfg = SnapshotConfig(enabled=True, path=str(tmp_path))
    _, hist = on_attempt_complete(cfg, "cmd", 1, "first", None, [])
    changed, hist = on_attempt_complete(cfg, "cmd", 2, "second", None, hist)
    assert changed is True
    assert hist[-1].changed is True


def test_parse_snapshot_missing_section_uses_defaults():
    cfg = parse_snapshot({})
    assert cfg.enabled is False


def test_parse_snapshot_full_section():
    cfg = parse_snapshot({"snapshot": {"enabled": True, "fail_on_change": True}})
    assert cfg.enabled is True
    assert cfg.fail_on_change is True


def test_parse_snapshot_invalid_type_raises():
    with pytest.raises(TypeError):
        parse_snapshot({"snapshot": "bad"})


def test_snapshot_config_to_dict_roundtrip():
    cfg = SnapshotConfig(enabled=True, compare_stderr=True)
    d = snapshot_config_to_dict(cfg)
    cfg2 = SnapshotConfig.from_dict(d)
    assert cfg2.enabled is True
    assert cfg2.compare_stderr is True


def test_describe_snapshot_disabled():
    assert "disabled" in describe_snapshot(SnapshotConfig())


def test_describe_snapshot_enabled():
    cfg = SnapshotConfig(enabled=True, compare_stdout=True, compare_stderr=True, fail_on_change=True)
    desc = describe_snapshot(cfg)
    assert "stdout" in desc
    assert "stderr" in desc
    assert "fail" in desc
