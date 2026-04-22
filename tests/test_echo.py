"""Tests for retryctl.echo and retryctl.echo_middleware."""
from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from retryctl.echo import (
    EchoConfig,
    EchoCacheEntry,
    _cache_path,
    load_echo_cache,
    save_echo_cache,
)
from retryctl.echo_middleware import (
    describe_echo,
    echo_config_to_dict,
    maybe_echo,
    on_run_success,
    parse_echo,
)


# ---------------------------------------------------------------------------
# EchoConfig
# ---------------------------------------------------------------------------

def test_config_defaults():
    cfg = EchoConfig()
    assert cfg.enabled is False
    assert cfg.ttl_seconds == 3600
    assert cfg.warn_on_echo is True


def test_from_dict_full():
    cfg = EchoConfig.from_dict({"enabled": True, "ttl_seconds": 60, "cache_dir": "/tmp/x", "warn_on_echo": False})
    assert cfg.enabled is True
    assert cfg.ttl_seconds == 60
    assert cfg.cache_dir == "/tmp/x"
    assert cfg.warn_on_echo is False


def test_from_dict_empty_uses_defaults():
    cfg = EchoConfig.from_dict({})
    assert cfg.enabled is False
    assert cfg.ttl_seconds == 3600


def test_from_dict_invalid_type_raises():
    with pytest.raises(TypeError):
        EchoConfig.from_dict("bad")


def test_from_dict_negative_ttl_raises():
    with pytest.raises(ValueError):
        EchoConfig.from_dict({"ttl_seconds": -1})


def test_from_dict_zero_ttl_allowed():
    cfg = EchoConfig.from_dict({"ttl_seconds": 0})
    assert cfg.ttl_seconds == 0


# ---------------------------------------------------------------------------
# Cache persistence
# ---------------------------------------------------------------------------

def test_save_and_load(tmp_path):
    cfg = EchoConfig(enabled=True, cache_dir=str(tmp_path))
    save_echo_cache(cfg, "mykey", "hello stdout", "hello stderr")
    entry = load_echo_cache(cfg, "mykey")
    assert entry is not None
    assert entry.stdout == "hello stdout"
    assert entry.stderr == "hello stderr"


def test_load_missing_returns_none(tmp_path):
    cfg = EchoConfig(enabled=True, cache_dir=str(tmp_path))
    assert load_echo_cache(cfg, "nokey") is None


def test_load_expired_returns_none(tmp_path):
    cfg = EchoConfig(enabled=True, cache_dir=str(tmp_path), ttl_seconds=1)
    save_echo_cache(cfg, "expkey", "out", "err")
    path = _cache_path(cfg, "expkey")
    data = json.loads(path.read_text())
    data["saved_at"] = time.time() - 10
    path.write_text(json.dumps(data))
    assert load_echo_cache(cfg, "expkey") is None


def test_load_zero_ttl_never_expires(tmp_path):
    cfg = EchoConfig(enabled=True, cache_dir=str(tmp_path), ttl_seconds=0)
    save_echo_cache(cfg, "zerokey", "out", "err")
    path = _cache_path(cfg, "zerokey")
    data = json.loads(path.read_text())
    data["saved_at"] = 0.0
    path.write_text(json.dumps(data))
    entry = load_echo_cache(cfg, "zerokey")
    assert entry is not None


# ---------------------------------------------------------------------------
# Middleware helpers
# ---------------------------------------------------------------------------

def test_parse_echo_empty_config():
    cfg = parse_echo({})
    assert cfg.enabled is False


def test_parse_echo_auto_enables_when_cache_dir_set():
    cfg = parse_echo({"echo": {"cache_dir": "/tmp/echo"}})
    assert cfg.enabled is True


def test_parse_echo_explicit_disabled_overrides():
    cfg = parse_echo({"echo": {"cache_dir": "/tmp/echo", "enabled": False}})
    assert cfg.enabled is False


def test_parse_echo_invalid_section_type_raises():
    with pytest.raises(TypeError):
        parse_echo({"echo": "not-a-dict"})


def test_echo_config_to_dict_roundtrip():
    cfg = EchoConfig(enabled=True, ttl_seconds=120, cache_dir="/x", warn_on_echo=False)
    d = echo_config_to_dict(cfg)
    cfg2 = EchoConfig.from_dict(d)
    assert cfg == cfg2


def test_on_run_success_saves_cache(tmp_path):
    cfg = EchoConfig(enabled=True, cache_dir=str(tmp_path))
    on_run_success(cfg, "k", "stdout", "stderr")
    entry = load_echo_cache(cfg, "k")
    assert entry is not None
    assert entry.stdout == "stdout"


def test_on_run_success_disabled_does_nothing(tmp_path):
    cfg = EchoConfig(enabled=False, cache_dir=str(tmp_path))
    on_run_success(cfg, "k", "stdout", "stderr")
    assert load_echo_cache(cfg, "k") is None


def test_maybe_echo_returns_none_when_disabled(tmp_path):
    cfg = EchoConfig(enabled=False, cache_dir=str(tmp_path))
    assert maybe_echo(cfg, "k") is None


def test_maybe_echo_returns_entry_when_cached(tmp_path):
    cfg = EchoConfig(enabled=True, cache_dir=str(tmp_path))
    save_echo_cache(cfg, "k", "o", "e")
    entry = maybe_echo(cfg, "k")
    assert entry is not None
    assert entry.stdout == "o"


def test_describe_echo_disabled():
    assert "disabled" in describe_echo(EchoConfig(enabled=False))


def test_describe_echo_enabled():
    desc = describe_echo(EchoConfig(enabled=True, ttl_seconds=60, cache_dir="/tmp"))
    assert "60" in desc
    assert "/tmp" in desc
