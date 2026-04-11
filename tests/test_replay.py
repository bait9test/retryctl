"""Tests for retryctl.replay and retryctl.replay_middleware."""
import json
import time
import pytest
from pathlib import Path

from retryctl.replay import (
    ReplayConfig,
    ReplayRecord,
    save_replay,
    load_replay,
    clear_replay,
    _replay_file,
)
from retryctl.replay_middleware import (
    parse_replay,
    replay_config_to_dict,
    on_run_failed,
    on_run_success,
    get_replay_command,
)


@pytest.fixture
def cfg(tmp_path):
    return ReplayConfig(enabled=True, replay_dir=str(tmp_path))


def test_config_defaults():
    c = ReplayConfig()
    assert c.enabled is False
    assert "retryctl" in c.replay_dir


def test_config_from_dict_full():
    c = ReplayConfig.from_dict({"enabled": True, "replay_dir": "/tmp/x"})
    assert c.enabled is True
    assert c.replay_dir == "/tmp/x"


def test_config_from_dict_empty():
    c = ReplayConfig.from_dict({})
    assert c.enabled is False


def test_config_from_dict_invalid_type_raises():
    with pytest.raises(TypeError):
        ReplayConfig.from_dict("bad")


def test_replay_record_roundtrip():
    r = ReplayRecord(command=["echo", "hi"], exit_code=1, attempt_count=3, label="job")
    restored = ReplayRecord.from_dict(r.to_dict())
    assert restored.command == ["echo", "hi"]
    assert restored.exit_code == 1
    assert restored.attempt_count == 3
    assert restored.label == "job"


def test_save_and_load(cfg):
    record = ReplayRecord(command=["false"], exit_code=1, label="t1")
    save_replay(cfg, record)
    loaded = load_replay(cfg, "t1")
    assert loaded is not None
    assert loaded.command == ["false"]
    assert loaded.exit_code == 1


def test_load_missing_returns_none(cfg):
    assert load_replay(cfg, "no-such-label") is None


def test_clear_removes_file(cfg):
    record = ReplayRecord(command=["ls"], exit_code=2, label="cl")
    save_replay(cfg, record)
    clear_replay(cfg, "cl")
    assert load_replay(cfg, "cl") is None


def test_disabled_config_skips_save(cfg, tmp_path):
    disabled = ReplayConfig(enabled=False, replay_dir=str(tmp_path))
    save_replay(disabled, ReplayRecord(command=["x"], exit_code=1))
    assert not any(tmp_path.iterdir())


def test_parse_replay_empty_config():
    cfg = parse_replay({})
    assert cfg.enabled is False


def test_parse_replay_full_section(tmp_path):
    cfg = parse_replay({"replay": {"enabled": True, "replay_dir": str(tmp_path)}})
    assert cfg.enabled is True


def test_parse_replay_invalid_type_raises():
    with pytest.raises(TypeError):
        parse_replay({"replay": "bad"})


def test_replay_config_to_dict_roundtrip(tmp_path):
    cfg = ReplayConfig(enabled=True, replay_dir=str(tmp_path))
    d = replay_config_to_dict(cfg)
    assert d["enabled"] is True
    assert d["replay_dir"] == str(tmp_path)


def test_on_run_failed_saves(tmp_path):
    cfg = ReplayConfig(enabled=True, replay_dir=str(tmp_path))
    on_run_failed(cfg, ["myapp", "--run"], 1, 2, label="myjob")
    loaded = load_replay(cfg, "myjob")
    assert loaded.command == ["myapp", "--run"]
    assert loaded.attempt_count == 2


def test_on_run_success_clears(tmp_path):
    cfg = ReplayConfig(enabled=True, replay_dir=str(tmp_path))
    save_replay(cfg, ReplayRecord(command=["x"], exit_code=1, label="j"))
    on_run_success(cfg, label="j")
    assert load_replay(cfg, "j") is None


def test_get_replay_command_returns_command(tmp_path):
    cfg = ReplayConfig(enabled=True, replay_dir=str(tmp_path))
    save_replay(cfg, ReplayRecord(command=["retry-me"], exit_code=1, label="r"))
    cmd = get_replay_command(cfg, "r")
    assert cmd == ["retry-me"]


def test_get_replay_command_none_when_missing(tmp_path):
    cfg = ReplayConfig(enabled=True, replay_dir=str(tmp_path))
    assert get_replay_command(cfg, "ghost") is None
