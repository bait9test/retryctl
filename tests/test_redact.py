"""Tests for retryctl.redact."""

import pytest
from retryctl.redact import RedactConfig, redact, redact_env


@pytest.fixture
def basic_cfg():
    return RedactConfig(patterns=[r"secret\S*", r"password=\S+"])


def test_from_dict_defaults():
    cfg = RedactConfig.from_dict({})
    assert cfg.enabled is True
    assert cfg.patterns == []
    assert cfg.placeholder == "***"


def test_from_dict_full():
    cfg = RedactConfig.from_dict(
        {"enabled": False, "patterns": [r"tok_\w+"], "placeholder": "<REDACTED>"}
    )
    assert cfg.enabled is False
    assert cfg.patterns == [r"tok_\w+"]
    assert cfg.placeholder == "<REDACTED>"


def test_redact_disabled_returns_original():
    cfg = RedactConfig(enabled=False, patterns=[r"\w+"])
    assert redact("hello world", cfg) == "hello world"


def test_redact_no_patterns_returns_original():
    cfg = RedactConfig(enabled=True, patterns=[])
    assert redact("sensitive data", cfg) == "sensitive data"


def test_redact_replaces_match(basic_cfg):
    result = redact("using secretABC here", basic_cfg)
    assert "secretABC" not in result
    assert "***" in result


def test_redact_replaces_multiple_patterns(basic_cfg):
    text = "secretXYZ and password=hunter2"
    result = redact(text, basic_cfg)
    assert "secretXYZ" not in result
    assert "hunter2" not in result
    assert result.count("***") == 2


def test_redact_no_match_returns_unchanged(basic_cfg):
    text = "nothing sensitive here"
    assert redact(text, basic_cfg) == text


def test_redact_custom_placeholder():
    cfg = RedactConfig(patterns=[r"token=\S+"], placeholder="<HIDDEN>")
    result = redact("token=abc123", cfg)
    assert "<HIDDEN>" in result
    assert "abc123" not in result


def test_invalid_pattern_skipped():
    cfg = RedactConfig(patterns=[r"[invalid", r"secret\S*"])
    result = redact("secretABC", cfg)
    # invalid pattern skipped, valid one still applied
    assert "secretABC" not in result


def test_redact_env_replaces_values():
    cfg = RedactConfig(patterns=[r"tok_\w+"])
    env = {"API_TOKEN": "tok_abc123", "HOME": "/home/user"}
    result = redact_env(env, cfg)
    assert result["API_TOKEN"] == "***"
    assert result["HOME"] == "/home/user"


def test_redact_env_disabled_unchanged():
    cfg = RedactConfig(enabled=False, patterns=[r"tok_\w+"])
    env = {"TOKEN": "tok_xyz"}
    assert redact_env(env, cfg) == env
