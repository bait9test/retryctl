"""Tests for retryctl.watch and retryctl.watch_context."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, call, patch

from retryctl.watch import WatchConfig, _snapshot, _changed, watch_for_change
from retryctl.watch_context import run_watch_loop


# ---------------------------------------------------------------------------
# WatchConfig
# ---------------------------------------------------------------------------

def test_config_defaults():
    cfg = WatchConfig()
    assert cfg.enabled is False
    assert cfg.paths == []
    assert cfg.poll_interval == 1.0
    assert cfg.debounce == 0.2
    assert cfg.max_triggers is None


def test_config_from_dict_full():
    cfg = WatchConfig.from_dict({
        "enabled": True,
        "paths": ["/tmp/a", "/tmp/b"],
        "poll_interval": 0.5,
        "debounce": 0.1,
        "max_triggers": 3,
    })
    assert cfg.enabled is True
    assert cfg.paths == ["/tmp/a", "/tmp/b"]
    assert cfg.poll_interval == 0.5
    assert cfg.debounce == 0.1
    assert cfg.max_triggers == 3


def test_config_from_dict_empty():
    cfg = WatchConfig.from_dict({})
    assert cfg.enabled is False
    assert cfg.max_triggers is None


# ---------------------------------------------------------------------------
# _snapshot / _changed
# ---------------------------------------------------------------------------

def test_snapshot_missing_file():
    snap = _snapshot(["/nonexistent/path/xyz"])
    assert snap["/nonexistent/path/xyz"] == 0.0


def test_changed_detects_mtime_diff():
    old = {"/a": 100.0, "/b": 200.0}
    new = {"/a": 100.0, "/b": 201.0}
    assert _changed(old, new) == ["/b"]


def test_changed_no_diff():
    snap = {"/a": 1.0}
    assert _changed(snap, snap) == []


# ---------------------------------------------------------------------------
# watch_for_change
# ---------------------------------------------------------------------------

def test_watch_for_change_raises_on_empty_paths():
    cfg = WatchConfig(paths=[])
    with pytest.raises(ValueError):
        watch_for_change(cfg)


def test_watch_for_change_returns_changed_paths(tmp_path):
    f = tmp_path / "file.txt"
    f.write_text("v1")
    cfg = WatchConfig(paths=[str(f)], poll_interval=0.0, debounce=0.0)

    call_count = 0

    def fake_sleep(secs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:          # first poll_interval sleep
            f.write_text("v2")       # mutate the file

    changed = watch_for_change(cfg, _sleep=fake_sleep)
    assert str(f) in changed


# ---------------------------------------------------------------------------
# run_watch_loop
# ---------------------------------------------------------------------------

def test_watch_loop_disabled_skips():
    cfg = WatchConfig(enabled=False)
    cb = MagicMock()
    run_watch_loop(cfg, cb)
    cb.assert_not_called()


def test_watch_loop_respects_max_triggers():
    cfg = WatchConfig(enabled=True, paths=["/x"], max_triggers=2)
    fake_watch = MagicMock(return_value=["/x"])
    cb = MagicMock()
    run_watch_loop(cfg, cb, _watch_fn=fake_watch)
    assert cb.call_count == 2


def test_watch_loop_callback_exception_does_not_stop_loop():
    cfg = WatchConfig(enabled=True, paths=["/x"], max_triggers=3)
    fake_watch = MagicMock(return_value=["/x"])
    cb = MagicMock(side_effect=RuntimeError("boom"))
    # should not raise
    run_watch_loop(cfg, cb, _watch_fn=fake_watch)
    assert cb.call_count == 3
