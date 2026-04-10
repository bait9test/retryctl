"""Tests for retryctl.profile_config integration helpers."""
from __future__ import annotations

import pytest

from retryctl.profile_config import list_profile_names, resolve_config_with_profile


_RAW = {
    "max_attempts": 5,
    "profiles": {
        "ci": {"max_attempts": 2, "description": "CI profile"},
        "prod": {"max_attempts": 10},
    },
}


def test_resolve_no_profile_returns_base():
    result = resolve_config_with_profile({"max_attempts": 3})
    assert result["max_attempts"] == 3
    assert "profiles" not in result


def test_resolve_with_override_applies_profile():
    result = resolve_config_with_profile(_RAW, profile_override="ci")
    assert result["max_attempts"] == 2
    assert "profiles" not in result


def test_resolve_with_unknown_profile_raises():
    with pytest.raises(KeyError, match="ghost"):
        resolve_config_with_profile(_RAW, profile_override="ghost")


def test_resolve_inline_profile_key_honoured():
    raw = dict(_RAW, profile="prod")
    result = resolve_config_with_profile(raw)
    assert result["max_attempts"] == 10


def test_resolve_override_beats_inline():
    raw = dict(_RAW, profile="prod")
    result = resolve_config_with_profile(raw, profile_override="ci")
    assert result["max_attempts"] == 2


def test_list_profile_names_sorted():
    names = list_profile_names(_RAW)
    assert names == ["ci", "prod"]


def test_list_profile_names_empty():
    assert list_profile_names({}) == []


def test_list_profile_names_no_profiles_key():
    assert list_profile_names({"max_attempts": 3}) == []
