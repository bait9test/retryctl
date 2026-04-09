"""Tests for retryctl.checkpoint and retryctl.checkpoint_context."""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from retryctl.checkpoint import (
    CheckpointConfig,
    CheckpointData,
    _checkpoint_path,
    clear_checkpoint,
    load_checkpoint,
    save_checkpoint,
)
from retryctl.checkpoint_context import (
    finish_checkpoint,
    resume_attempt,
    update_checkpoint,
)


@pytest.fixture()
def tmp_cfg(tmp_path: Path) -> CheckpointConfig:
    return CheckpointConfig(enabled=True, directory=str(tmp_path), ttl_seconds=3600)


# --- CheckpointConfig ---

def test_config_defaults():
    cfg = CheckpointConfig()
    assert cfg.enabled is False
    assert cfg.ttl_seconds == 3600


def test_config_from_dict():
    cfg = CheckpointConfig.from_dict({"enabled": True, "ttl_seconds": 60, "directory": "/x"})
    assert cfg.enabled is True
    assert cfg.ttl_seconds == 60
    assert cfg.directory == "/x"


# --- CheckpointData ---

def test_checkpoint_data_roundtrip():
    d = CheckpointData(command="echo hi", attempt=3, last_exit_code=1)
    restored = CheckpointData.from_dict(d.to_dict())
    assert restored.command == "echo hi"
    assert restored.attempt == 3
    assert restored.last_exit_code == 1


# --- save / load / clear ---

def test_save_and_load(tmp_cfg):
    data = CheckpointData(command="my cmd", attempt=2, last_exit_code=127)
    save_checkpoint(tmp_cfg, data)
    loaded = load_checkpoint(tmp_cfg, "my cmd")
    assert loaded is not None
    assert loaded.attempt == 2
    assert loaded.last_exit_code == 127


def test_load_returns_none_when_disabled(tmp_path):
    cfg = CheckpointConfig(enabled=False, directory=str(tmp_path))
    assert load_checkpoint(cfg, "cmd") is None


def test_load_returns_none_when_missing(tmp_cfg):
    assert load_checkpoint(tmp_cfg, "nonexistent cmd") is None


def test_load_evicts_stale_checkpoint(tmp_cfg):
    cfg = CheckpointConfig(enabled=True, directory=tmp_cfg.directory, ttl_seconds=1)
    data = CheckpointData(command="stale", attempt=1, started_at=time.time() - 10)
    save_checkpoint(cfg, data)
    assert load_checkpoint(cfg, "stale") is None
    # file should be gone
    assert not _checkpoint_path(cfg, "stale").exists()


def test_clear_removes_file(tmp_cfg):
    data = CheckpointData(command="removeme", attempt=1)
    save_checkpoint(tmp_cfg, data)
    clear_checkpoint(tmp_cfg, "removeme")
    assert not _checkpoint_path(tmp_cfg, "removeme").exists()


def test_save_disabled_does_nothing(tmp_path):
    cfg = CheckpointConfig(enabled=False, directory=str(tmp_path))
    save_checkpoint(cfg, CheckpointData(command="x", attempt=0))
    assert list(tmp_path.iterdir()) == []


# --- checkpoint_context ---

def test_resume_attempt_no_checkpoint(tmp_cfg):
    assert resume_attempt(tmp_cfg, "fresh cmd") == 0


def test_resume_attempt_with_checkpoint(tmp_cfg):
    data = CheckpointData(command="my cmd", attempt=4)
    save_checkpoint(tmp_cfg, data)
    assert resume_attempt(tmp_cfg, "my cmd") == 4


def test_update_checkpoint_persists(tmp_cfg):
    update_checkpoint(tmp_cfg, "my cmd", attempt=2, exit_code=1)
    loaded = load_checkpoint(tmp_cfg, "my cmd")
    assert loaded is not None and loaded.attempt == 2


def test_finish_checkpoint_clears(tmp_cfg):
    update_checkpoint(tmp_cfg, "my cmd", attempt=1, exit_code=1)
    finish_checkpoint(tmp_cfg, "my cmd")
    assert load_checkpoint(tmp_cfg, "my cmd") is None
