"""Tests for retryctl.cooldown and retryctl.cooldown_middleware."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from retryctl.cooldown import (
    CooldownConfig,
    CooldownBlocked,
    _sanitise_key,
    _state_path,
    check_cooldown,
    record_success,
    clear_cooldown,
)
from retryctl.cooldown_middleware import (
    parse_cooldown,
    cooldown_config_to_dict,
    enforce_cooldown_gate,
    on_run_success,
    on_run_reset,
)


# ---------------------------------------------------------------------------
# CooldownConfig
# ---------------------------------------------------------------------------

def test_config_defaults():
    cfg = CooldownConfig()
    assert cfg.enabled is False
    assert cfg.seconds == 60.0
    assert cfg.key == ""


def test_config_from_dict_full():
    cfg = CooldownConfig.from_dict({"enabled": True, "seconds": 30, "key": "myjob"})
    assert cfg.enabled is True
    assert cfg.seconds == 30.0
    assert cfg.key == "myjob"


def test_config_from_dict_empty():
    cfg = CooldownConfig.from_dict({})
    assert cfg.enabled is False
    assert cfg.seconds == 60.0


def test_config_negative_seconds_raises():
    with pytest.raises(ValueError, match="non-negative"):
        CooldownConfig.from_dict({"seconds": -1})


# ---------------------------------------------------------------------------
# _sanitise_key
# ---------------------------------------------------------------------------

def test_sanitise_key_replaces_spaces():
    assert " " not in _sanitise_key("my job")


def test_sanitise_key_truncates():
    long_key = "a" * 100
    assert len(_sanitise_key(long_key)) <= 64


def test_sanitise_key_empty_becomes_default():
    assert _sanitise_key("") == "default"


# ---------------------------------------------------------------------------
# record_success / check_cooldown / clear_cooldown
# ---------------------------------------------------------------------------

def test_disabled_config_skips_all(tmp_path):
    cfg = CooldownConfig(enabled=False, lock_dir=str(tmp_path))
    record_success(cfg, "cmd")
    assert not any(tmp_path.iterdir())  # nothing written
    check_cooldown(cfg, "cmd")  # should not raise


def test_record_and_check_within_window(tmp_path):
    cfg = CooldownConfig(enabled=True, seconds=60.0, lock_dir=str(tmp_path))
    record_success(cfg, "cmd")
    with pytest.raises(CooldownBlocked) as exc_info:
        check_cooldown(cfg, "cmd")
    assert exc_info.value.remaining > 0


def test_check_after_window_passes(tmp_path):
    cfg = CooldownConfig(enabled=True, seconds=1.0, lock_dir=str(tmp_path))
    path = _state_path(cfg, "cmd")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"last_success": time.time() - 5}))
    check_cooldown(cfg, "cmd")  # should not raise


def test_clear_removes_state(tmp_path):
    cfg = CooldownConfig(enabled=True, seconds=60.0, lock_dir=str(tmp_path))
    record_success(cfg, "cmd")
    clear_cooldown(cfg, "cmd")
    check_cooldown(cfg, "cmd")  # no state file → should not raise


def test_corrupt_state_file_does_not_raise(tmp_path):
    cfg = CooldownConfig(enabled=True, seconds=60.0, lock_dir=str(tmp_path))
    path = _state_path(cfg, "cmd")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("not-json")
    check_cooldown(cfg, "cmd")  # should not raise


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

def test_parse_cooldown_reads_section():
    cfg = parse_cooldown({"cooldown": {"enabled": True, "seconds": 10}})
    assert cfg.enabled is True
    assert cfg.seconds == 10.0


def test_parse_cooldown_missing_section_gives_defaults():
    cfg = parse_cooldown({})
    assert cfg.enabled is False


def test_parse_cooldown_wrong_type_raises():
    with pytest.raises(TypeError):
        parse_cooldown({"cooldown": "bad"})


def test_cooldown_config_to_dict_roundtrip():
    cfg = CooldownConfig(enabled=True, seconds=45.0, key="k", lock_dir="/tmp")
    d = cooldown_config_to_dict(cfg)
    assert d["enabled"] is True
    assert d["seconds"] == 45.0
    assert d["key"] == "k"


def test_enforce_gate_disabled_does_not_raise(tmp_path):
    cfg = CooldownConfig(enabled=False, lock_dir=str(tmp_path))
    enforce_cooldown_gate(cfg, "cmd")  # should not raise


def test_on_run_success_then_gate_blocks(tmp_path):
    cfg = CooldownConfig(enabled=True, seconds=60.0, lock_dir=str(tmp_path))
    on_run_success(cfg, "cmd")
    with pytest.raises(CooldownBlocked):
        enforce_cooldown_gate(cfg, "cmd")


def test_on_run_reset_clears_block(tmp_path):
    cfg = CooldownConfig(enabled=True, seconds=60.0, lock_dir=str(tmp_path))
    on_run_success(cfg, "cmd")
    on_run_reset(cfg, "cmd")
    enforce_cooldown_gate(cfg, "cmd")  # should not raise after reset
