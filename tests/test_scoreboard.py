"""Tests for retryctl.scoreboard and retryctl.scoreboard_middleware."""
from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from retryctl.scoreboard import ScoreboardConfig, ScoreboardTracker
from retryctl.scoreboard_middleware import (
    describe_scoreboard,
    parse_scoreboard,
    record_run_outcome,
    scoreboard_config_to_dict,
)


# ---------------------------------------------------------------------------
# ScoreboardConfig
# ---------------------------------------------------------------------------

def test_config_defaults():
    cfg = ScoreboardConfig()
    assert cfg.enabled is False
    assert cfg.window_seconds == 3600


def test_config_from_dict_full():
    cfg = ScoreboardConfig.from_dict({"enabled": True, "file": "/tmp/sb.json", "window_seconds": 600})
    assert cfg.enabled is True
    assert cfg.file == "/tmp/sb.json"
    assert cfg.window_seconds == 600


def test_config_from_dict_empty_uses_defaults():
    cfg = ScoreboardConfig.from_dict({})
    assert cfg.enabled is False
    assert cfg.window_seconds == 3600


def test_config_invalid_type_raises():
    with pytest.raises(TypeError):
        ScoreboardConfig.from_dict("bad")


def test_config_zero_window_raises():
    with pytest.raises(ValueError):
        ScoreboardConfig.from_dict({"window_seconds": 0})


def test_config_negative_window_raises():
    with pytest.raises(ValueError):
        ScoreboardConfig.from_dict({"window_seconds": -1})


# ---------------------------------------------------------------------------
# ScoreboardTracker
# ---------------------------------------------------------------------------

@pytest.fixture()
def tmp_cfg(tmp_path):
    return ScoreboardConfig(enabled=True, file=str(tmp_path / "sb.json"), window_seconds=60)


def test_record_disabled_does_nothing(tmp_path):
    cfg = ScoreboardConfig(enabled=False, file=str(tmp_path / "sb.json"))
    tracker = ScoreboardTracker(config=cfg)
    tracker.record("cmd", succeeded=True)
    assert not Path(cfg.file).exists()


def test_record_creates_file(tmp_cfg):
    tracker = ScoreboardTracker(config=tmp_cfg)
    tracker.record("cmd", succeeded=True)
    assert Path(tmp_cfg.file).exists()


def test_summary_counts(tmp_cfg):
    tracker = ScoreboardTracker(config=tmp_cfg)
    tracker.record("cmd", succeeded=True)
    tracker.record("cmd", succeeded=False)
    tracker.record("cmd", succeeded=True)
    s = tracker.summary("cmd")["cmd"]
    assert s["attempts"] == 3
    assert s["successes"] == 2
    assert s["failures"] == 1
    assert s["ratio"] == pytest.approx(2 / 3, rel=1e-3)


def test_summary_filters_by_key(tmp_cfg):
    tracker = ScoreboardTracker(config=tmp_cfg)
    tracker.record("a", succeeded=True)
    tracker.record("b", succeeded=False)
    s = tracker.summary(key="a")
    assert "a" in s
    assert "b" not in s


def test_summary_evicts_old_entries(tmp_cfg):
    tracker = ScoreboardTracker(config=tmp_cfg)
    old_entry = type(tracker._entries.append.__self__
                     if hasattr(tracker._entries, '__self__') else tracker._entries)
    # Manually inject a stale entry
    from retryctl.scoreboard import ScoreEntry
    tracker._entries.append(ScoreEntry(key="cmd", ts=time.time() - 9999, succeeded=True))
    tracker.record("cmd", succeeded=False)  # triggers persist + eviction
    s = tracker.summary("cmd")
    # only the fresh failure should remain
    assert s["cmd"]["attempts"] == 1
    assert s["cmd"]["failures"] == 1


def test_load_reads_persisted_data(tmp_cfg):
    tracker = ScoreboardTracker(config=tmp_cfg)
    tracker.record("cmd", succeeded=True)
    loaded = ScoreboardTracker.load(tmp_cfg)
    assert loaded.summary("cmd")["cmd"]["successes"] == 1


def test_load_missing_file_returns_empty(tmp_cfg):
    tracker = ScoreboardTracker.load(tmp_cfg)
    assert tracker.summary() == {}


def test_load_corrupt_file_returns_empty(tmp_cfg):
    Path(tmp_cfg.file).write_text("not json")
    tracker = ScoreboardTracker.load(tmp_cfg)
    assert tracker.summary() == {}


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

def test_parse_scoreboard_empty_config():
    cfg = parse_scoreboard({})
    assert cfg.enabled is False


def test_parse_scoreboard_full_section():
    cfg = parse_scoreboard({"scoreboard": {"enabled": True, "window_seconds": 120}})
    assert cfg.enabled is True
    assert cfg.window_seconds == 120


def test_parse_scoreboard_invalid_section_raises():
    with pytest.raises(TypeError):
        parse_scoreboard({"scoreboard": "bad"})


def test_scoreboard_config_to_dict_roundtrip():
    cfg = ScoreboardConfig(enabled=True, file="/tmp/x.json", window_seconds=300)
    d = scoreboard_config_to_dict(cfg)
    assert d == {"enabled": True, "file": "/tmp/x.json", "window_seconds": 300}


def test_record_run_outcome_delegates(tmp_cfg):
    tracker = ScoreboardTracker(config=tmp_cfg)
    record_run_outcome(tracker, "my-cmd", succeeded=True)
    assert tracker.summary("my-cmd")["my-cmd"]["successes"] == 1


def test_describe_scoreboard_disabled():
    cfg = ScoreboardConfig(enabled=False)
    assert "disabled" in describe_scoreboard(cfg)


def test_describe_scoreboard_no_data(tmp_cfg):
    result = describe_scoreboard(tmp_cfg)
    assert "no data" in result


def test_describe_scoreboard_with_data(tmp_cfg):
    tracker = ScoreboardTracker(config=tmp_cfg)
    tracker.record("deploy", succeeded=False)
    result = describe_scoreboard(tmp_cfg, key="deploy")
    assert "deploy" in result
    assert "1 attempts" in result
