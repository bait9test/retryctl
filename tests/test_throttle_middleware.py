"""Tests for retryctl/throttle_middleware.py."""
import pytest

from retryctl.throttle import ThrottleConfig
from retryctl.throttle_middleware import (
    describe_throttle,
    parse_throttle,
    throttle_config_to_dict,
)


# ---------------------------------------------------------------------------
# parse_throttle
# ---------------------------------------------------------------------------

def test_parse_throttle_empty_config_uses_defaults():
    cfg = parse_throttle({})
    assert cfg.enabled is False
    assert cfg.key is None
    assert cfg.lock_dir == "/tmp/retryctl/throttle"
    assert cfg.timeout == 30


def test_parse_throttle_missing_section_uses_defaults():
    cfg = parse_throttle({"other": {}})
    assert cfg.enabled is False


def test_parse_throttle_full_section():
    raw = {
        "throttle": {
            "enabled": True,
            "key": "deploy-job",
            "lock_dir": "/var/lock/retryctl",
            "timeout": 60,
        }
    }
    cfg = parse_throttle(raw)
    assert cfg.enabled is True
    assert cfg.key == "deploy-job"
    assert cfg.lock_dir == "/var/lock/retryctl"
    assert cfg.timeout == 60


def test_parse_throttle_auto_enables_when_key_set():
    raw = {"throttle": {"key": "my-key"}}
    cfg = parse_throttle(raw)
    assert cfg.enabled is True


def test_parse_throttle_explicit_disabled_overrides_key():
    raw = {"throttle": {"key": "my-key", "enabled": False}}
    cfg = parse_throttle(raw)
    assert cfg.enabled is False


def test_parse_throttle_invalid_section_type_raises():
    with pytest.raises(TypeError):
        parse_throttle({"throttle": "not-a-dict"})


def test_parse_throttle_timeout_coerced_to_int():
    raw = {"throttle": {"timeout": "45"}}
    cfg = parse_throttle(raw)
    assert cfg.timeout == 45


# ---------------------------------------------------------------------------
# throttle_config_to_dict
# ---------------------------------------------------------------------------

def test_throttle_config_to_dict_roundtrip():
    raw = {
        "throttle": {
            "enabled": True,
            "key": "job-x",
            "lock_dir": "/tmp/locks",
            "timeout": 10,
        }
    }
    cfg = parse_throttle(raw)
    d = throttle_config_to_dict(cfg)
    assert d["enabled"] is True
    assert d["key"] == "job-x"
    assert d["lock_dir"] == "/tmp/locks"
    assert d["timeout"] == 10


def test_throttle_config_to_dict_defaults():
    cfg = parse_throttle({})
    d = throttle_config_to_dict(cfg)
    assert d["enabled"] is False
    assert d["key"] is None


# ---------------------------------------------------------------------------
# describe_throttle
# ---------------------------------------------------------------------------

def test_describe_throttle_disabled():
    cfg = parse_throttle({})
    desc = describe_throttle(cfg)
    assert "disabled" in desc


def test_describe_throttle_enabled_with_key():
    raw = {"throttle": {"key": "build", "lock_dir": "/tmp", "timeout": 5}}
    cfg = parse_throttle(raw)
    desc = describe_throttle(cfg)
    assert "build" in desc
    assert "5s" in desc
    assert "disabled" not in desc


def test_describe_throttle_enabled_no_key_shows_default_label():
    cfg = ThrottleConfig(enabled=True, key=None, lock_dir="/tmp", timeout=10)
    desc = describe_throttle(cfg)
    assert "<default>" in desc
