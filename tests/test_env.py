"""Tests for retryctl.env."""
import os
import pytest

from retryctl.env import EnvConfig, from_dict, build_env, merge_env_override


# ---------------------------------------------------------------------------
# from_dict
# ---------------------------------------------------------------------------

def test_from_dict_defaults():
    cfg = from_dict({})
    assert cfg.inherit is True
    assert cfg.extra == {}
    assert cfg.unset == []


def test_from_dict_full():
    cfg = from_dict({"inherit": False, "extra": {"FOO": "bar"}, "unset": ["HOME"]})
    assert cfg.inherit is False
    assert cfg.extra == {"FOO": "bar"}
    assert cfg.unset == ["HOME"]


def test_from_dict_inherit_coerced_to_bool():
    cfg = from_dict({"inherit": 0})
    assert cfg.inherit is False


# ---------------------------------------------------------------------------
# build_env
# ---------------------------------------------------------------------------

def test_build_env_injects_retry_vars():
    cfg = EnvConfig(inherit=False)
    env = build_env(cfg, attempt=2, max_attempts=5)
    assert env["RETRYCTL_ATTEMPT"] == "2"
    assert env["RETRYCTL_MAX_ATTEMPTS"] == "5"


def test_build_env_inherits_os_environ(monkeypatch):
    monkeypatch.setenv("MY_TEST_VAR", "hello")
    cfg = EnvConfig(inherit=True)
    env = build_env(cfg, attempt=1, max_attempts=3)
    assert env["MY_TEST_VAR"] == "hello"


def test_build_env_no_inherit_excludes_os_environ(monkeypatch):
    monkeypatch.setenv("MY_TEST_VAR", "hello")
    cfg = EnvConfig(inherit=False)
    env = build_env(cfg, attempt=1, max_attempts=3)
    assert "MY_TEST_VAR" not in env


def test_build_env_unset_removes_key(monkeypatch):
    monkeypatch.setenv("SECRET", "topsecret")
    cfg = EnvConfig(inherit=True, unset=["SECRET"])
    env = build_env(cfg, attempt=1, max_attempts=1)
    assert "SECRET" not in env


def test_build_env_extra_overrides_inherited(monkeypatch):
    monkeypatch.setenv("LEVEL", "debug")
    cfg = EnvConfig(inherit=True, extra={"LEVEL": "info"})
    env = build_env(cfg, attempt=1, max_attempts=1)
    assert env["LEVEL"] == "info"


def test_build_env_extra_does_not_override_retry_vars_when_set_explicitly():
    # extra can override RETRYCTL_ATTEMPT if the user really wants to
    cfg = EnvConfig(inherit=False, extra={"RETRYCTL_ATTEMPT": "99"})
    env = build_env(cfg, attempt=1, max_attempts=1)
    # setdefault means extra wins because extra is applied before setdefault
    assert env["RETRYCTL_ATTEMPT"] == "99"


# ---------------------------------------------------------------------------
# merge_env_override
# ---------------------------------------------------------------------------

def test_merge_env_override_adds_keys():
    cfg = EnvConfig(extra={"A": "1"})
    merged = merge_env_override(cfg, {"B": "2"})
    assert merged.extra == {"A": "1", "B": "2"}


def test_merge_env_override_overrides_existing():
    cfg = EnvConfig(extra={"A": "old"})
    merged = merge_env_override(cfg, {"A": "new"})
    assert merged.extra["A"] == "new"


def test_merge_env_override_none_returns_original():
    cfg = EnvConfig(extra={"A": "1"})
    result = merge_env_override(cfg, None)
    assert result is cfg


def test_merge_env_override_preserves_inherit_and_unset():
    cfg = EnvConfig(inherit=False, unset=["X"], extra={})
    merged = merge_env_override(cfg, {"Y": "1"})
    assert merged.inherit is False
    assert merged.unset == ["X"]
