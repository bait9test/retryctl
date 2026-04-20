"""Tests for retryctl.banner and retryctl.banner_middleware."""
from __future__ import annotations

import pytest

from retryctl.banner import BannerConfig, build_banner_lines, emit_banner
from retryctl.banner_middleware import (
    banner_config_to_dict,
    before_run,
    describe_banner,
    parse_banner,
)


# ---------------------------------------------------------------------------
# BannerConfig.from_dict
# ---------------------------------------------------------------------------

def test_from_dict_defaults():
    cfg = BannerConfig.from_dict({})
    assert cfg.enabled is False
    assert cfg.show_command is True
    assert cfg.show_config is False
    assert cfg.show_version is True
    assert cfg.prefix == "[retryctl]"


def test_from_dict_full():
    cfg = BannerConfig.from_dict(
        {"enabled": True, "show_command": False, "show_config": True,
         "show_version": False, "prefix": ">>"}
    )
    assert cfg.enabled is True
    assert cfg.show_command is False
    assert cfg.show_config is True
    assert cfg.show_version is False
    assert cfg.prefix == ">>"


def test_from_dict_invalid_type_raises():
    with pytest.raises(TypeError):
        BannerConfig.from_dict("not-a-dict")  # type: ignore[arg-type]


def test_from_dict_coerces_enabled_to_bool():
    cfg = BannerConfig.from_dict({"enabled": 1})
    assert cfg.enabled is True


# ---------------------------------------------------------------------------
# build_banner_lines
# ---------------------------------------------------------------------------

def test_disabled_returns_empty():
    cfg = BannerConfig(enabled=False)
    assert build_banner_lines(cfg, command=["echo", "hi"], version="1.0") == []


def test_enabled_shows_version():
    cfg = BannerConfig(enabled=True, show_version=True, show_command=False)
    lines = build_banner_lines(cfg, version="2.3.4")
    assert any("2.3.4" in l for l in lines)


def test_enabled_shows_command():
    cfg = BannerConfig(enabled=True, show_command=True, show_version=False)
    lines = build_banner_lines(cfg, command=["my-cmd", "--flag"])
    assert any("my-cmd --flag" in l for l in lines)


def test_enabled_shows_config_path():
    cfg = BannerConfig(enabled=True, show_config=True, show_version=False)
    lines = build_banner_lines(cfg, config_path="/etc/retryctl.toml")
    assert any("/etc/retryctl.toml" in l for l in lines)


def test_no_config_path_skips_config_line():
    cfg = BannerConfig(enabled=True, show_config=True, show_version=False)
    lines = build_banner_lines(cfg, config_path=None)
    assert lines == []


def test_prefix_appears_in_lines():
    cfg = BannerConfig(enabled=True, prefix="##", show_version=True)
    lines = build_banner_lines(cfg, version="0.1")
    assert all(l.startswith("##") for l in lines)


# ---------------------------------------------------------------------------
# emit_banner (smoke — just ensure it doesn't raise)
# ---------------------------------------------------------------------------

def test_emit_banner_smoke(caplog):
    import logging
    cfg = BannerConfig(enabled=True, show_version=True)
    with caplog.at_level(logging.INFO, logger="retryctl.banner"):
        emit_banner(cfg, version="9.9.9")
    assert any("9.9.9" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

def test_parse_banner_empty_config():
    cfg = parse_banner({})
    assert isinstance(cfg, BannerConfig)
    assert cfg.enabled is False


def test_parse_banner_full_section():
    cfg = parse_banner({"banner": {"enabled": True, "prefix": "--"}})
    assert cfg.enabled is True
    assert cfg.prefix == "--"


def test_parse_banner_missing_section_uses_defaults():
    cfg = parse_banner({"other": {}})
    assert cfg.enabled is False


def test_parse_banner_invalid_type_raises():
    with pytest.raises(TypeError):
        parse_banner({"banner": "bad"})


def test_banner_config_to_dict_roundtrip():
    original = BannerConfig(enabled=True, show_config=True, prefix="!")
    d = banner_config_to_dict(original)
    restored = BannerConfig.from_dict(d)
    assert restored == original


def test_describe_banner_disabled():
    assert "disabled" in describe_banner(BannerConfig(enabled=False))


def test_describe_banner_enabled_lists_shown():
    cfg = BannerConfig(enabled=True, show_version=True, show_command=True, show_config=False)
    desc = describe_banner(cfg)
    assert "version" in desc
    assert "command" in desc


def test_before_run_smoke(caplog):
    import logging
    cfg = BannerConfig(enabled=True, show_version=True)
    with caplog.at_level(logging.INFO, logger="retryctl.banner"):
        before_run(cfg, command=["ls"], version="1.2.3")
    assert any("1.2.3" in r.message for r in caplog.records)
