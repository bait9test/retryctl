"""Tests for retryctl.backpressure and retryctl.backpressure_middleware."""
from __future__ import annotations

import pytest

from retryctl.backpressure import BackpressureConfig, _read_load, apply_backpressure
from retryctl.backpressure_middleware import (
    backpressure_config_to_dict,
    describe_backpressure,
    maybe_apply_backpressure,
    parse_backpressure,
)


# ---------------------------------------------------------------------------
# BackpressureConfig.from_dict
# ---------------------------------------------------------------------------

def test_config_defaults():
    cfg = BackpressureConfig.from_dict({})
    assert cfg.enabled is False
    assert cfg.source_file is None
    assert cfg.source_cmd is None
    assert cfg.threshold == 1.0
    assert cfg.penalty_seconds == 5.0
    assert cfg.max_penalty_seconds == 60.0


def test_config_from_dict_full():
    cfg = BackpressureConfig.from_dict({
        "enabled": True,
        "source_file": "/proc/loadavg",
        "threshold": 2.5,
        "penalty_seconds": 10.0,
        "max_penalty_seconds": 120.0,
    })
    assert cfg.enabled is True
    assert cfg.source_file == "/proc/loadavg"
    assert cfg.threshold == 2.5
    assert cfg.penalty_seconds == 10.0
    assert cfg.max_penalty_seconds == 120.0


def test_config_auto_enables_when_source_file_set():
    cfg = BackpressureConfig.from_dict({"source_file": "/proc/loadavg"})
    assert cfg.enabled is True


def test_config_auto_enables_when_source_cmd_set():
    cfg = BackpressureConfig.from_dict({"source_cmd": "uptime | awk '{print $NF}'"})
    assert cfg.enabled is True


def test_config_both_sources_raises():
    with pytest.raises(ValueError, match="source_file or source_cmd"):
        BackpressureConfig.from_dict({
            "source_file": "/proc/loadavg",
            "source_cmd": "echo 0",
        })


def test_config_negative_penalty_raises():
    with pytest.raises(ValueError, match="penalty_seconds"):
        BackpressureConfig.from_dict({"penalty_seconds": -1.0})


def test_config_max_less_than_penalty_raises():
    with pytest.raises(ValueError, match="max_penalty_seconds"):
        BackpressureConfig.from_dict({"penalty_seconds": 30.0, "max_penalty_seconds": 5.0})


def test_config_invalid_type_raises():
    with pytest.raises(TypeError):
        BackpressureConfig.from_dict("not-a-dict")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# _read_load
# ---------------------------------------------------------------------------

def test_read_load_from_file(tmp_path):
    f = tmp_path / "load.txt"
    f.write_text("3.14 1.00 0.50\n")
    cfg = BackpressureConfig(enabled=True, source_file=str(f))
    assert _read_load(cfg) == pytest.approx(3.14)


def test_read_load_missing_file_returns_none():
    cfg = BackpressureConfig(enabled=True, source_file="/nonexistent/load.txt")
    assert _read_load(cfg) is None


def test_read_load_from_cmd():
    cfg = BackpressureConfig(enabled=True, source_cmd="echo 2.71")
    assert _read_load(cfg) == pytest.approx(2.71)


def test_read_load_bad_cmd_returns_none():
    cfg = BackpressureConfig(enabled=True, source_cmd="echo not-a-number")
    assert _read_load(cfg) is None


# ---------------------------------------------------------------------------
# apply_backpressure
# ---------------------------------------------------------------------------

def test_apply_backpressure_disabled_does_not_sleep(mocker):
    sleep = mocker.patch("retryctl.backpressure.time.sleep")
    cfg = BackpressureConfig(enabled=False)
    apply_backpressure(cfg, attempt=1)
    sleep.assert_not_called()


def test_apply_backpressure_below_threshold_no_sleep(tmp_path, mocker):
    f = tmp_path / "load.txt"
    f.write_text("0.5")
    sleep = mocker.patch("retryctl.backpressure.time.sleep")
    cfg = BackpressureConfig(enabled=True, source_file=str(f), threshold=1.0, penalty_seconds=5.0)
    apply_backpressure(cfg, attempt=1)
    sleep.assert_not_called()


def test_apply_backpressure_above_threshold_sleeps(tmp_path, mocker):
    f = tmp_path / "load.txt"
    f.write_text("4.0")
    sleep = mocker.patch("retryctl.backpressure.time.sleep")
    cfg = BackpressureConfig(
        enabled=True, source_file=str(f), threshold=1.0,
        penalty_seconds=5.0, max_penalty_seconds=60.0,
    )
    apply_backpressure(cfg, attempt=1)
    sleep.assert_called_once()
    args, _ = sleep.call_args
    assert args[0] == pytest.approx(20.0)  # ratio=4, penalty=5*4=20


def test_apply_backpressure_caps_at_max(tmp_path, mocker):
    f = tmp_path / "load.txt"
    f.write_text("100.0")
    sleep = mocker.patch("retryctl.backpressure.time.sleep")
    cfg = BackpressureConfig(
        enabled=True, source_file=str(f), threshold=1.0,
        penalty_seconds=5.0, max_penalty_seconds=30.0,
    )
    apply_backpressure(cfg, attempt=1)
    args, _ = sleep.call_args
    assert args[0] == pytest.approx(30.0)


# ---------------------------------------------------------------------------
# middleware helpers
# ---------------------------------------------------------------------------

def test_parse_backpressure_empty_config():
    cfg = parse_backpressure({})
    assert cfg.enabled is False


def test_parse_backpressure_full_section():
    cfg = parse_backpressure({"backpressure": {"source_cmd": "echo 0", "threshold": 3.0}})
    assert cfg.enabled is True
    assert cfg.threshold == 3.0


def test_parse_backpressure_invalid_type_raises():
    with pytest.raises(TypeError):
        parse_backpressure({"backpressure": "bad"})


def test_backpressure_config_to_dict_roundtrip():
    cfg = BackpressureConfig(enabled=True, source_cmd="echo 1", threshold=2.0,
                             penalty_seconds=8.0, max_penalty_seconds=40.0)
    d = backpressure_config_to_dict(cfg)
    assert d["enabled"] is True
    assert d["source_cmd"] == "echo 1"
    assert d["threshold"] == 2.0


def test_maybe_apply_backpressure_disabled(mocker):
    apply = mocker.patch("retryctl.backpressure_middleware.apply_backpressure")
    cfg = BackpressureConfig(enabled=False)
    maybe_apply_backpressure(cfg, attempt=1)
    apply.assert_not_called()


def test_maybe_apply_backpressure_enabled(mocker):
    apply = mocker.patch("retryctl.backpressure_middleware.apply_backpressure")
    cfg = BackpressureConfig(enabled=True, source_cmd="echo 0")
    maybe_apply_backpressure(cfg, attempt=2)
    apply.assert_called_once_with(cfg, 2)


def test_describe_backpressure_disabled():
    cfg = BackpressureConfig(enabled=False)
    assert describe_backpressure(cfg) == "backpressure: disabled"


def test_describe_backpressure_enabled():
    cfg = BackpressureConfig(enabled=True, source_file="/proc/loadavg",
                             threshold=1.5, penalty_seconds=10.0, max_penalty_seconds=60.0)
    desc = describe_backpressure(cfg)
    assert "enabled" in desc
    assert "/proc/loadavg" in desc
    assert "1.5" in desc
