"""Integration-style tests combining tag config with label tags."""
from __future__ import annotations

from retryctl.label import LabelConfig, from_dict as label_from_dict
from retryctl.tag import TagFilterConfig, check_tag_gate
from retryctl.tag_middleware import enforce_tag_gate, TagGateBlocked

import pytest


def _label(tags=None, name=None):
    data = {}
    if name:
        data["name"] = name
    if tags is not None:
        data["tags"] = tags
    return label_from_dict(data)


def test_label_tags_pass_gate():
    label = _label(tags=["prod", "eu-west"])
    cfg = TagFilterConfig(require_any=["prod"])
    assert check_tag_gate(label.tags, cfg) is None


def test_label_tags_fail_gate():
    label = _label(tags=["staging"])
    cfg = TagFilterConfig(require_any=["prod"])
    reason = check_tag_gate(label.tags, cfg)
    assert reason is not None


def test_label_tags_blocked():
    label = _label(tags=["debug", "prod"])
    cfg = TagFilterConfig(block=["debug"])
    with pytest.raises(TagGateBlocked):
        enforce_tag_gate(label.tags, cfg)


def test_empty_label_tags_no_requirements_passes():
    label = _label(tags=[])
    cfg = TagFilterConfig()
    assert check_tag_gate(label.tags, cfg) is None


def test_empty_label_tags_with_requirements_fails():
    label = _label(tags=[])
    cfg = TagFilterConfig(require_any=["prod"])
    reason = check_tag_gate(label.tags, cfg)
    assert reason is not None


def test_multiple_block_tags_any_triggers():
    label = _label(tags=["canary", "unsafe"])
    cfg = TagFilterConfig(block=["unsafe", "danger"])
    reason = check_tag_gate(label.tags, cfg)
    assert reason is not None
    assert "unsafe" in reason


def test_enforce_no_raise_with_label_tags():
    label = _label(tags=["staging"])
    cfg = TagFilterConfig(require_any=["prod"])
    result = enforce_tag_gate(label.tags, cfg, raise_on_block=False)
    assert result is not None
    assert "requires" in result
