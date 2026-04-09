"""Integration-style tests: NotifyConfig round-trips through from_dict."""
from __future__ import annotations

import pytest

from retryctl.notify import NotifyConfig, NotifyLevel


@pytest.mark.parametrize("level_str,expected", [
    ("always", NotifyLevel.ALWAYS),
    ("failure", NotifyLevel.FAILURE),
    ("never", NotifyLevel.NEVER),
])
def test_from_dict_all_levels(level_str, expected):
    cfg = NotifyConfig.from_dict({"level": level_str})
    assert cfg.level == expected


def test_from_dict_empty_uses_defaults():
    cfg = NotifyConfig.from_dict({})
    assert cfg.level == NotifyLevel.NEVER
    assert cfg.title == "retryctl"
    assert cfg.sound is False
    assert cfg.extra_args == []


def test_from_dict_extra_args_preserved():
    cfg = NotifyConfig.from_dict({"extra_args": ["--a", "--b"], "level": "always"})
    assert cfg.extra_args == ["--a", "--b"]


def test_from_dict_sound_coerced_to_bool():
    cfg = NotifyConfig.from_dict({"sound": 1})
    assert cfg.sound is True
    cfg2 = NotifyConfig.from_dict({"sound": 0})
    assert cfg2.sound is False


def test_notify_config_repr_contains_level():
    cfg = NotifyConfig(level=NotifyLevel.ALWAYS)
    # dataclass __repr__ should include field names
    assert "ALWAYS" in repr(cfg)
