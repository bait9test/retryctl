"""Tests for retryctl.mirror and retryctl.mirror_middleware."""
from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

from retryctl.mirror import MirrorConfig, MirrorResult, mirror_output
from retryctl.mirror_middleware import (
    describe_mirror,
    mirror_config_to_dict,
    on_attempt_complete,
    parse_mirror,
)


# ---------------------------------------------------------------------------
# MirrorConfig.from_dict
# ---------------------------------------------------------------------------

def test_config_defaults():
    cfg = MirrorConfig.from_dict({})
    assert cfg.enabled is False
    assert cfg.output_file is None
    assert cfg.pipe_cmd is None
    assert cfg.on_failure_only is False


def test_config_from_dict_full():
    cfg = MirrorConfig.from_dict({
        "enabled": True,
        "output_file": "/tmp/out.log",
        "pipe_cmd": ["cat", "-n"],
        "on_failure_only": True,
    })
    assert cfg.enabled is True
    assert cfg.output_file == "/tmp/out.log"
    assert cfg.pipe_cmd == ["cat", "-n"]
    assert cfg.on_failure_only is True


def test_config_string_pipe_cmd_splits():
    cfg = MirrorConfig.from_dict({"pipe_cmd": "tee /tmp/x.log"})
    assert cfg.pipe_cmd == ["tee", "/tmp/x.log"]


def test_config_invalid_type_raises():
    with pytest.raises(TypeError):
        MirrorConfig.from_dict("bad")


def test_config_invalid_pipe_cmd_type_raises():
    with pytest.raises(TypeError):
        MirrorConfig.from_dict({"pipe_cmd": 42})


def test_config_auto_enables_when_output_file_set():
    cfg = MirrorConfig.from_dict({"output_file": "/tmp/mirror.log"})
    assert cfg.enabled is True


def test_config_auto_enables_when_pipe_cmd_set():
    cfg = MirrorConfig.from_dict({"pipe_cmd": "logger -t retryctl"})
    assert cfg.enabled is True


# ---------------------------------------------------------------------------
# mirror_output
# ---------------------------------------------------------------------------

def test_mirror_disabled_returns_empty():
    cfg = MirrorConfig(enabled=False)
    result = mirror_output(cfg, "hello\n", "", 1)
    assert result.lines_written == 0
    assert result.pipe_returncode is None
    assert result.error is None


def test_on_failure_only_skips_success():
    cfg = MirrorConfig(enabled=True, on_failure_only=True, output_file="/tmp/x")
    with patch("builtins.open", MagicMock()) as m:
        result = mirror_output(cfg, "ok", "", 0)
    assert result.lines_written == 0
    m.assert_not_called()


def test_writes_to_file(tmp_path):
    out = tmp_path / "mirror.log"
    cfg = MirrorConfig(enabled=True, output_file=str(out))
    result = mirror_output(cfg, "line1", "line2", 1)
    assert result.error is None
    assert result.lines_written == 2
    content = out.read_text()
    assert "line1" in content
    assert "line2" in content


def test_file_write_error_captured(tmp_path):
    cfg = MirrorConfig(enabled=True, output_file="/no/such/dir/file.log")
    result = mirror_output(cfg, "data", "", 0)
    assert result.error is not None


def test_pipe_cmd_called():
    cfg = MirrorConfig(enabled=True, pipe_cmd=["cat"])
    result = mirror_output(cfg, "hello", "", 0)
    assert result.pipe_returncode == 0
    assert result.error is None


# ---------------------------------------------------------------------------
# middleware helpers
# ---------------------------------------------------------------------------

def test_parse_mirror_missing_section_uses_defaults():
    cfg = parse_mirror({})
    assert cfg.enabled is False


def test_parse_mirror_full_section():
    cfg = parse_mirror({"mirror": {"enabled": True, "on_failure_only": True}})
    assert cfg.enabled is True
    assert cfg.on_failure_only is True


def test_parse_mirror_invalid_type_raises():
    with pytest.raises(TypeError):
        parse_mirror({"mirror": "bad"})


def test_mirror_config_to_dict_roundtrip():
    cfg = MirrorConfig(enabled=True, output_file="/tmp/a", pipe_cmd=["tee"], on_failure_only=False)
    d = mirror_config_to_dict(cfg)
    cfg2 = MirrorConfig.from_dict(d)
    assert cfg2.output_file == cfg.output_file
    assert cfg2.pipe_cmd == cfg.pipe_cmd


def test_describe_mirror_disabled():
    cfg = MirrorConfig(enabled=False)
    assert "disabled" in describe_mirror(cfg)


def test_describe_mirror_enabled_with_file():
    cfg = MirrorConfig(enabled=True, output_file="/tmp/m.log")
    desc = describe_mirror(cfg)
    assert "file=" in desc
    assert "/tmp/m.log" in desc


def test_describe_mirror_on_failure_only():
    cfg = MirrorConfig(enabled=True, pipe_cmd=["logger"], on_failure_only=True)
    desc = describe_mirror(cfg)
    assert "failure only" in desc


def test_on_attempt_complete_disabled_no_log(caplog):
    cfg = MirrorConfig(enabled=False)
    result = on_attempt_complete(cfg, "out", "err", 1)
    assert result.lines_written == 0
