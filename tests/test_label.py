"""Tests for retryctl.label and retryctl.label_middleware."""

from __future__ import annotations

import pytest

from retryctl.label import LabelConfig, format_label, label_to_dict
from retryctl.label_middleware import build_label_env, _ENV_LABEL_KEY, _ENV_TAG_PREFIX


# ---------------------------------------------------------------------------
# LabelConfig.from_dict
# ---------------------------------------------------------------------------

def test_from_dict_defaults():
    cfg = LabelConfig.from_dict({})
    assert cfg.name is None
    assert cfg.tags == {}


def test_from_dict_name_only():
    cfg = LabelConfig.from_dict({"name": "smoke-test"})
    assert cfg.name == "smoke-test"
    assert cfg.tags == {}


def test_from_dict_tags_coerced_to_str():
    cfg = LabelConfig.from_dict({"tags": {"attempt": 3, "env": "staging"}})
    assert cfg.tags == {"attempt": "3", "env": "staging"}


def test_from_dict_invalid_tags_raises():
    with pytest.raises(ValueError, match="mapping"):
        LabelConfig.from_dict({"tags": "not-a-dict"})


def test_from_dict_empty_name_becomes_none():
    cfg = LabelConfig.from_dict({"name": ""})
    assert cfg.name is None


# ---------------------------------------------------------------------------
# format_label
# ---------------------------------------------------------------------------

def test_format_label_unlabelled():
    assert format_label(LabelConfig()) == "(unlabelled)"


def test_format_label_name_only():
    assert format_label(LabelConfig(name="deploy")) == "deploy"


def test_format_label_tags_only():
    result = format_label(LabelConfig(tags={"env": "prod", "region": "us-east"}))
    assert result == "[env=prod region=us-east]"


def test_format_label_name_and_tags():
    result = format_label(LabelConfig(name="migrate", tags={"db": "main"}))
    assert result == "migrate [db=main]"


def test_format_label_tags_sorted():
    result = format_label(LabelConfig(tags={"z": "last", "a": "first"}))
    assert result == "[a=first z=last]"


# ---------------------------------------------------------------------------
# label_to_dict
# ---------------------------------------------------------------------------

def test_label_to_dict_roundtrip():
    cfg = LabelConfig(name="ci", tags={"branch": "main"})
    d = label_to_dict(cfg)
    assert d == {"name": "ci", "tags": {"branch": "main"}}


def test_label_to_dict_none_name():
    d = label_to_dict(LabelConfig())
    assert d["name"] is None
    assert d["tags"] == {}


# ---------------------------------------------------------------------------
# build_label_env
# ---------------------------------------------------------------------------

def test_build_label_env_injects_name():
    cfg = LabelConfig(name="retryctl-job")
    env = build_label_env(cfg, base={})
    assert env[_ENV_LABEL_KEY] == "retryctl-job"


def test_build_label_env_no_name_removes_key():
    base = {_ENV_LABEL_KEY: "old-value"}
    env = build_label_env(LabelConfig(), base=base)
    assert _ENV_LABEL_KEY not in env


def test_build_label_env_injects_tags():
    cfg = LabelConfig(tags={"env": "prod", "region": "eu"})
    env = build_label_env(cfg, base={})
    assert env[_ENV_TAG_PREFIX + "ENV"] == "prod"
    assert env[_ENV_TAG_PREFIX + "REGION"] == "eu"


def test_build_label_env_clears_stale_tags():
    base = {_ENV_TAG_PREFIX + "OLD": "stale"}
    env = build_label_env(LabelConfig(tags={"new": "val"}), base=base)
    assert _ENV_TAG_PREFIX + "OLD" not in env
    assert env[_ENV_TAG_PREFIX + "NEW"] == "val"


def test_build_label_env_tag_key_normalised():
    cfg = LabelConfig(tags={"my-tag": "value"})
    env = build_label_env(cfg, base={})
    assert env[_ENV_TAG_PREFIX + "MY_TAG"] == "value"


def test_build_label_env_defaults_to_os_environ(monkeypatch):
    monkeypatch.setenv("EXISTING_VAR", "hello")
    cfg = LabelConfig(name="x")
    env = build_label_env(cfg)
    assert env.get("EXISTING_VAR") == "hello"
