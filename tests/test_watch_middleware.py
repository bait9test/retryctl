"""Tests for retryctl.watch_middleware."""
from __future__ import annotations

import pytest

from retryctl.watch import WatchConfig
from retryctl.watch_middleware import parse_watch, watch_config_to_dict


def test_parse_watch_empty_config():
    cfg = parse_watch({})
    assert isinstance(cfg, WatchConfig)
    assert cfg.enabled is False


def test_parse_watch_full_section():
    raw = {
        "watch": {
            "enabled": True,
            "paths": ["/var/log/app.log"],
            "poll_interval": 2.0,
            "debounce": 0.5,
            "max_triggers": 10,
        }
    }
    cfg = parse_watch(raw)
    assert cfg.enabled is True
    assert cfg.paths == ["/var/log/app.log"]
    assert cfg.max_triggers == 10


def test_parse_watch_missing_section_uses_defaults():
    cfg = parse_watch({"other_key": 42})
    assert cfg.enabled is False
    assert cfg.paths == []


def test_parse_watch_invalid_type_raises():
    with pytest.raises(TypeError):
        parse_watch({"watch": "not-a-dict"})


def test_watch_config_to_dict_roundtrip():
    original = WatchConfig(
        enabled=True,
        paths=["/tmp/x"],
        poll_interval=0.5,
        debounce=0.1,
        max_triggers=5,
    )
    d = watch_config_to_dict(original)
    restored = WatchConfig.from_dict(d)
    assert restored.enabled == original.enabled
    assert restored.paths == original.paths
    assert restored.poll_interval == original.poll_interval
    assert restored.debounce == original.debounce
    assert restored.max_triggers == original.max_triggers


def test_watch_config_to_dict_none_max_triggers():
    cfg = WatchConfig()
    d = watch_config_to_dict(cfg)
    assert d["max_triggers"] is None
