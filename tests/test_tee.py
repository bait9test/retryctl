"""Tests for retryctl/tee.py."""
from __future__ import annotations

import io
import os
import pytest

from retryctl.tee import TeeConfig, TeeResult, apply_tee, tee_lines


# ---------------------------------------------------------------------------
# TeeConfig
# ---------------------------------------------------------------------------

def test_config_defaults():
    cfg = TeeConfig()
    assert cfg.enabled is False
    assert cfg.stdout_file is None
    assert cfg.stderr_file is None
    assert cfg.append is False


def test_from_dict_empty_uses_defaults():
    cfg = TeeConfig.from_dict({})
    assert cfg.enabled is False


def test_from_dict_full():
    cfg = TeeConfig.from_dict(
        {"enabled": True, "stdout_file": "/tmp/out.log", "stderr_file": "/tmp/err.log", "append": True}
    )
    assert cfg.enabled is True
    assert cfg.stdout_file == "/tmp/out.log"
    assert cfg.stderr_file == "/tmp/err.log"
    assert cfg.append is True


def test_from_dict_auto_enables_when_stdout_file_set():
    cfg = TeeConfig.from_dict({"stdout_file": "/tmp/out.log"})
    assert cfg.enabled is True


def test_from_dict_auto_enables_when_stderr_file_set():
    cfg = TeeConfig.from_dict({"stderr_file": "/tmp/err.log"})
    assert cfg.enabled is True


def test_from_dict_invalid_type_raises():
    with pytest.raises(TypeError):
        TeeConfig.from_dict("bad")


# ---------------------------------------------------------------------------
# TeeResult
# ---------------------------------------------------------------------------

def test_tee_result_stdout_property():
    r = TeeResult(stdout_lines=["hello\n", "world\n"])
    assert r.stdout == "hello\nworld\n"


def test_tee_result_stderr_property():
    r = TeeResult(stderr_lines=["err\n"])
    assert r.stderr == "err\n"


def test_tee_result_empty_by_default():
    r = TeeResult()
    assert r.stdout == ""
    assert r.stderr == ""


# ---------------------------------------------------------------------------
# tee_lines
# ---------------------------------------------------------------------------

def test_tee_lines_writes_to_stream():
    buf = io.StringIO()
    tee_lines(["line1\n", "line2\n"], buf, None, False)
    assert buf.getvalue() == "line1\nline2\n"


def test_tee_lines_writes_to_file(tmp_path):
    out = tmp_path / "out.txt"
    buf = io.StringIO()
    tee_lines(["hello\n"], buf, str(out), False)
    assert out.read_text() == "hello\n"


def test_tee_lines_appends_to_file(tmp_path):
    out = tmp_path / "out.txt"
    out.write_text("existing\n")
    buf = io.StringIO()
    tee_lines(["new\n"], buf, str(out), append=True)
    assert out.read_text() == "existing\nnew\n"


# ---------------------------------------------------------------------------
# apply_tee
# ---------------------------------------------------------------------------

def test_apply_tee_disabled_does_nothing(tmp_path, capsys):
    cfg = TeeConfig(enabled=False, stdout_file=str(tmp_path / "out.txt"))
    result = TeeResult(stdout_lines=["ignored\n"])
    apply_tee(cfg, result)
    captured = capsys.readouterr()
    assert captured.out == ""
    assert not (tmp_path / "out.txt").exists()


def test_apply_tee_writes_stdout(tmp_path, capsys):
    out_file = tmp_path / "stdout.log"
    cfg = TeeConfig(enabled=True, stdout_file=str(out_file))
    result = TeeResult(stdout_lines=["hello\n"])
    apply_tee(cfg, result)
    captured = capsys.readouterr()
    assert captured.out == "hello\n"
    assert out_file.read_text() == "hello\n"


def test_apply_tee_writes_stderr(tmp_path, capsys):
    err_file = tmp_path / "stderr.log"
    cfg = TeeConfig(enabled=True, stderr_file=str(err_file))
    result = TeeResult(stderr_lines=["oops\n"])
    apply_tee(cfg, result)
    captured = capsys.readouterr()
    assert captured.err == "oops\n"
    assert err_file.read_text() == "oops\n"
