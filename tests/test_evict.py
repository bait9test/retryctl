"""Tests for retryctl.evict and retryctl.evict_middleware."""
from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from retryctl.evict import (
    EvictBlocked,
    EvictConfig,
    _cache_path,
    _sanitise_key,
    check_evict_gate,
    record_evict_success,
)
from retryctl.evict_middleware import (
    before_run,
    describe_evict,
    evict_config_to_dict,
    on_run_success,
    parse_evict,
    resolve_key,
)


# ---------------------------------------------------------------------------
# EvictConfig
# ---------------------------------------------------------------------------

def test_config_defaults():
    cfg = EvictConfig()
    assert cfg.enabled is False
    assert cfg.ttl_seconds == 300.0
    assert cfg.key is None


def test_from_dict_full():
    cfg = EvictConfig.from_dict({"enabled": True, "ttl_seconds": 60, "key": "my-job"})
    assert cfg.enabled is True
    assert cfg.ttl_seconds == 60.0
    assert cfg.key == "my-job"


def test_from_dict_empty_uses_defaults():
    cfg = EvictConfig.from_dict({})
    assert cfg.enabled is False
    assert cfg.ttl_seconds == 300.0


def test_from_dict_auto_enables_when_key_set():
    cfg = EvictConfig.from_dict({"key": "auto"})
    assert cfg.enabled is True


def test_from_dict_invalid_type_raises():
    with pytest.raises(TypeError):
        EvictConfig.from_dict("bad")


def test_from_dict_zero_ttl_raises():
    with pytest.raises(ValueError):
        EvictConfig.from_dict({"enabled": True, "ttl_seconds": 0})


def test_from_dict_negative_ttl_raises():
    with pytest.raises(ValueError):
        EvictConfig.from_dict({"ttl_seconds": -5})


# ---------------------------------------------------------------------------
# _sanitise_key
# ---------------------------------------------------------------------------

def test_sanitise_key_replaces_spaces():
    assert " " not in _sanitise_key("hello world")


def test_sanitise_key_truncates_long_keys():
    assert len(_sanitise_key("x" * 200)) <= 64


def test_sanitise_key_preserves_alphanumeric():
    assert _sanitise_key("abc-123_OK") == "abc-123_OK"


# ---------------------------------------------------------------------------
# check_evict_gate / record_evict_success
# ---------------------------------------------------------------------------

@pytest.fixture()
def tmp_cfg(tmp_path):
    return EvictConfig(enabled=True, ttl_seconds=60.0, cache_dir=str(tmp_path))


def test_disabled_config_never_blocks(tmp_path):
    cfg = EvictConfig(enabled=False, cache_dir=str(tmp_path))
    # should not raise even if we write a fake cache entry
    check_evict_gate(cfg, "any-key")


def test_no_cache_entry_does_not_block(tmp_cfg):
    check_evict_gate(tmp_cfg, "missing-key")  # should not raise


def test_valid_cache_entry_blocks(tmp_cfg):
    record_evict_success(tmp_cfg, "my-key")
    with pytest.raises(EvictBlocked) as exc_info:
        check_evict_gate(tmp_cfg, "my-key")
    assert "my-key" in str(exc_info.value)
    assert exc_info.value.expires_in > 0


def test_expired_cache_entry_does_not_block(tmp_cfg, tmp_path):
    path = _cache_path(tmp_cfg, "old-key")
    path.parent.mkdir(parents=True, exist_ok=True)
    # write an already-expired entry
    path.write_text(json.dumps({"key": "old-key", "expires_at": time.monotonic() - 1}))
    check_evict_gate(tmp_cfg, "old-key")  # should not raise
    assert not path.exists()  # stale entry removed


# ---------------------------------------------------------------------------
# Middleware helpers
# ---------------------------------------------------------------------------

def test_parse_evict_empty_config():
    cfg = parse_evict({})
    assert cfg.enabled is False


def test_parse_evict_full_section():
    cfg = parse_evict({"evict": {"enabled": True, "ttl_seconds": 30, "key": "k"}})
    assert cfg.enabled is True
    assert cfg.ttl_seconds == 30.0


def test_parse_evict_invalid_section_type_raises():
    with pytest.raises(TypeError):
        parse_evict({"evict": "bad"})


def test_evict_config_to_dict_roundtrip():
    cfg = EvictConfig(enabled=True, ttl_seconds=45.0, key="job")
    d = evict_config_to_dict(cfg)
    assert d["enabled"] is True
    assert d["ttl_seconds"] == 45.0
    assert d["key"] == "job"


def test_resolve_key_uses_explicit_key():
    cfg = EvictConfig(enabled=True, key="explicit")
    assert resolve_key(cfg, "echo hi") == "explicit"


def test_resolve_key_falls_back_to_command_hash():
    cfg = EvictConfig(enabled=True)
    key = resolve_key(cfg, "echo hi")
    assert key.startswith("cmd_")


def test_before_run_blocks_when_cached(tmp_cfg):
    record_evict_success(tmp_cfg, resolve_key(tmp_cfg, "echo hi"))
    with pytest.raises(EvictBlocked):
        before_run(tmp_cfg, "echo hi")


def test_on_run_success_creates_cache(tmp_cfg):
    on_run_success(tmp_cfg, "echo hi")
    key = resolve_key(tmp_cfg, "echo hi")
    path = _cache_path(tmp_cfg, key)
    assert path.exists()


def test_describe_evict_disabled():
    cfg = EvictConfig(enabled=False)
    assert "disabled" in describe_evict(cfg)


def test_describe_evict_enabled_with_key():
    cfg = EvictConfig(enabled=True, ttl_seconds=120.0, key="myjob")
    desc = describe_evict(cfg)
    assert "myjob" in desc
    assert "120.0" in desc
