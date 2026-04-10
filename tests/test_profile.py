"""Tests for retryctl.profile and retryctl.profile_middleware."""
from __future__ import annotations

import pytest

from retryctl.profile import (
    Profile,
    from_dict,
    load_profiles,
    merge_profile,
    resolve_profile,
)
from retryctl.profile_middleware import apply_profile, describe_profiles


# ---------------------------------------------------------------------------
# from_dict
# ---------------------------------------------------------------------------

def test_from_dict_basic():
    p = from_dict("fast", {"description": "Quick retries", "max_attempts": 3})
    assert p.name == "fast"
    assert p.description == "Quick retries"
    assert p.settings == {"max_attempts": 3}


def test_from_dict_no_description():
    p = from_dict("silent", {"max_attempts": 5})
    assert p.description == ""
    assert "max_attempts" in p.settings


def test_from_dict_empty():
    p = from_dict("empty", {})
    assert p.settings == {}
    assert p.description == ""


def test_from_dict_wrong_type_raises():
    with pytest.raises(TypeError, match="must be a table"):
        from_dict("bad", "not-a-dict")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# load_profiles
# ---------------------------------------------------------------------------

def test_load_profiles_returns_all():
    raw = {
        "fast": {"max_attempts": 2},
        "slow": {"max_attempts": 10, "description": "patient"},
    }
    profiles = load_profiles(raw)
    assert set(profiles) == {"fast", "slow"}
    assert profiles["slow"].description == "patient"


def test_load_profiles_empty():
    assert load_profiles({}) == {}


# ---------------------------------------------------------------------------
# resolve_profile
# ---------------------------------------------------------------------------

def test_resolve_profile_none_returns_none():
    assert resolve_profile({}, None) is None


def test_resolve_profile_found():
    profiles = {"fast": Profile(name="fast", settings={"max_attempts": 2})}
    p = resolve_profile(profiles, "fast")
    assert p is not None
    assert p.name == "fast"


def test_resolve_profile_missing_raises():
    profiles = {"fast": Profile(name="fast")}
    with pytest.raises(KeyError, match="Available profiles: fast"):
        resolve_profile(profiles, "unknown")


# ---------------------------------------------------------------------------
# merge_profile
# ---------------------------------------------------------------------------

def test_merge_profile_none_returns_copy():
    base = {"max_attempts": 5}
    result = merge_profile(base, None)
    assert result == base
    assert result is not base


def test_merge_profile_overrides_base():
    base = {"max_attempts": 5, "backoff": "fixed"}
    p = Profile(name="fast", settings={"max_attempts": 2})
    result = merge_profile(base, p)
    assert result["max_attempts"] == 2
    assert result["backoff"] == "fixed"  # untouched


# ---------------------------------------------------------------------------
# apply_profile (middleware)
# ---------------------------------------------------------------------------

def test_apply_profile_no_profiles_section():
    cfg = {"max_attempts": 3}
    result = apply_profile(cfg)
    assert result == {"max_attempts": 3}


def test_apply_profile_strips_profiles_key():
    cfg = {"profiles": {"fast": {"max_attempts": 2}}, "max_attempts": 5}
    result = apply_profile(cfg, "fast")
    assert "profiles" not in result
    assert result["max_attempts"] == 2


def test_apply_profile_uses_inline_profile_key():
    cfg = {
        "profile": "fast",
        "profiles": {"fast": {"max_attempts": 1}},
        "max_attempts": 5,
    }
    result = apply_profile(cfg)  # no explicit name
    assert result["max_attempts"] == 1


def test_apply_profile_explicit_overrides_inline():
    cfg = {
        "profile": "slow",
        "profiles": {
            "fast": {"max_attempts": 1},
            "slow": {"max_attempts": 99},
        },
    }
    result = apply_profile(cfg, profile_name="fast")
    assert result["max_attempts"] == 1


# ---------------------------------------------------------------------------
# describe_profiles
# ---------------------------------------------------------------------------

def test_describe_profiles_empty():
    assert describe_profiles({}) == "No profiles defined."


def test_describe_profiles_lists_names():
    cfg = {
        "profiles": {
            "fast": {"description": "Quick", "max_attempts": 2},
            "slow": {"max_attempts": 10},
        }
    }
    out = describe_profiles(cfg)
    assert "fast" in out
    assert "slow" in out
    assert "Quick" in out
