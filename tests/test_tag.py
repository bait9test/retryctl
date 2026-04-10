"""Tests for retryctl.tag and retryctl.tag_middleware."""
from __future__ import annotations

import pytest

from retryctl.tag import (
    TagFilterConfig,
    check_tag_gate,
    is_blocked,
    meets_requirements,
)
from retryctl.tag_middleware import (
    TagGateBlocked,
    enforce_tag_gate,
    parse_tag_filter,
    tag_filter_to_dict,
)


# ---------------------------------------------------------------------------
# TagFilterConfig.from_dict
# ---------------------------------------------------------------------------

def test_from_dict_defaults():
    cfg = TagFilterConfig.from_dict({})
    assert cfg.require_any == []
    assert cfg.block == []


def test_from_dict_full():
    cfg = TagFilterConfig.from_dict({"require_any": ["prod", "staging"], "block": ["debug"]})
    assert "prod" in cfg.require_any
    assert "debug" in cfg.block


def test_from_dict_coerces_to_str():
    cfg = TagFilterConfig.from_dict({"block": [1, 2]})
    assert cfg.block == ["1", "2"]


# ---------------------------------------------------------------------------
# is_blocked / meets_requirements
# ---------------------------------------------------------------------------

def test_is_blocked_true():
    cfg = TagFilterConfig(block=["danger"])
    assert is_blocked(["prod", "danger"], cfg) is True


def test_is_blocked_false():
    cfg = TagFilterConfig(block=["danger"])
    assert is_blocked(["prod", "staging"], cfg) is False


def test_meets_requirements_no_require_any():
    cfg = TagFilterConfig()
    assert meets_requirements([], cfg) is True


def test_meets_requirements_match():
    cfg = TagFilterConfig(require_any=["prod", "canary"])
    assert meets_requirements(["canary", "eu"], cfg) is True


def test_meets_requirements_no_match():
    cfg = TagFilterConfig(require_any=["prod"])
    assert meets_requirements(["staging"], cfg) is False


# ---------------------------------------------------------------------------
# check_tag_gate
# ---------------------------------------------------------------------------

def test_check_tag_gate_allowed():
    cfg = TagFilterConfig(require_any=["prod"], block=["debug"])
    assert check_tag_gate(["prod"], cfg) is None


def test_check_tag_gate_blocked_takes_priority():
    cfg = TagFilterConfig(require_any=["prod"], block=["prod"])
    reason = check_tag_gate(["prod"], cfg)
    assert reason is not None
    assert "blocked" in reason


def test_check_tag_gate_unmet_requirement():
    cfg = TagFilterConfig(require_any=["prod"])
    reason = check_tag_gate(["staging"], cfg)
    assert reason is not None
    assert "requires" in reason


# ---------------------------------------------------------------------------
# middleware helpers
# ---------------------------------------------------------------------------

def test_parse_tag_filter_empty_config():
    cfg = parse_tag_filter({})
    assert cfg.require_any == []


def test_parse_tag_filter_with_section():
    cfg = parse_tag_filter({"tag_filter": {"block": ["debug"]}})
    assert "debug" in cfg.block


def test_parse_tag_filter_invalid_type_raises():
    with pytest.raises(TypeError):
        parse_tag_filter({"tag_filter": "not-a-dict"})


def test_tag_filter_to_dict_roundtrip():
    cfg = TagFilterConfig(require_any=["prod"], block=["debug"])
    d = tag_filter_to_dict(cfg)
    restored = TagFilterConfig.from_dict(d)
    assert restored.require_any == cfg.require_any
    assert restored.block == cfg.block


def test_enforce_tag_gate_allowed_returns_none():
    cfg = TagFilterConfig()
    assert enforce_tag_gate(["any"], cfg) is None


def test_enforce_tag_gate_raises_when_blocked():
    cfg = TagFilterConfig(block=["danger"])
    with pytest.raises(TagGateBlocked):
        enforce_tag_gate(["danger"], cfg)


def test_enforce_tag_gate_no_raise_returns_reason():
    cfg = TagFilterConfig(block=["danger"])
    reason = enforce_tag_gate(["danger"], cfg, raise_on_block=False)
    assert reason is not None
    assert "danger" in reason
