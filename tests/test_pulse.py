"""Tests for retryctl.pulse and retryctl.pulse_middleware."""
from __future__ import annotations

import time
from unittest.mock import MagicMock

import pytest

from retryctl.pulse import PulseConfig, PulseEmitter, describe_pulse
from retryctl.pulse_middleware import (
    describe,
    make_emitter,
    parse_pulse,
    pulse_config_to_dict,
)


# ---------------------------------------------------------------------------
# PulseConfig
# ---------------------------------------------------------------------------

def test_config_defaults():
    cfg = PulseConfig()
    assert cfg.enabled is False
    assert cfg.interval_seconds == 30.0
    assert cfg.channel == "log"


def test_from_dict_full():
    cfg = PulseConfig.from_dict({"enabled": True, "interval_seconds": 10, "channel": "stderr", "message": "alive"})
    assert cfg.enabled is True
    assert cfg.interval_seconds == 10.0
    assert cfg.channel == "stderr"
    assert cfg.message == "alive"


def test_from_dict_empty_uses_defaults():
    cfg = PulseConfig.from_dict({})
    assert cfg.enabled is False
    assert cfg.interval_seconds == 30.0


def test_from_dict_invalid_type_raises():
    with pytest.raises(TypeError):
        PulseConfig.from_dict("bad")


def test_from_dict_negative_interval_raises():
    with pytest.raises(ValueError):
        PulseConfig.from_dict({"interval_seconds": -1})


def test_from_dict_zero_interval_raises():
    with pytest.raises(ValueError):
        PulseConfig.from_dict({"interval_seconds": 0})


def test_from_dict_invalid_channel_raises():
    with pytest.raises(ValueError):
        PulseConfig.from_dict({"channel": "slack"})


# ---------------------------------------------------------------------------
# PulseEmitter
# ---------------------------------------------------------------------------

def test_disabled_emitter_never_emits():
    cfg = PulseConfig(enabled=False, interval_seconds=0.01)
    emitter = PulseEmitter(config=cfg)
    cb = MagicMock()
    time.sleep(0.02)
    result = emitter.maybe_emit(attempt=1, emit_fn=cb)
    assert result is False
    cb.assert_not_called()


def test_emits_after_interval(monkeypatch):
    cfg = PulseConfig(enabled=True, interval_seconds=0.01)
    emitter = PulseEmitter(config=cfg)
    cb = MagicMock()
    time.sleep(0.02)
    result = emitter.maybe_emit(attempt=2, emit_fn=cb)
    assert result is True
    cb.assert_called_once()
    assert "2" in cb.call_args[0][0]


def test_does_not_emit_before_interval():
    cfg = PulseConfig(enabled=True, interval_seconds=60)
    emitter = PulseEmitter(config=cfg)
    cb = MagicMock()
    result = emitter.maybe_emit(attempt=1, emit_fn=cb)
    assert result is False
    cb.assert_not_called()


def test_reset_delays_next_pulse():
    cfg = PulseConfig(enabled=True, interval_seconds=0.01)
    emitter = PulseEmitter(config=cfg)
    time.sleep(0.02)
    emitter.reset()
    cb = MagicMock()
    result = emitter.maybe_emit(attempt=1, emit_fn=cb)
    assert result is False


# ---------------------------------------------------------------------------
# describe_pulse
# ---------------------------------------------------------------------------

def test_describe_disabled():
    assert describe_pulse(PulseConfig()) == "pulse disabled"


def test_describe_enabled():
    cfg = PulseConfig(enabled=True, interval_seconds=15, channel="stderr")
    assert "15" in describe_pulse(cfg)
    assert "stderr" in describe_pulse(cfg)


# ---------------------------------------------------------------------------
# Middleware helpers
# ---------------------------------------------------------------------------

def test_parse_pulse_empty_config():
    cfg = parse_pulse({})
    assert cfg.enabled is False


def test_parse_pulse_full_section():
    cfg = parse_pulse({"pulse": {"enabled": True, "interval_seconds": 5}})
    assert cfg.enabled is True
    assert cfg.interval_seconds == 5.0


def test_parse_pulse_missing_section_uses_defaults():
    cfg = parse_pulse({"backoff": {}})
    assert cfg.enabled is False


def test_parse_pulse_invalid_type_raises():
    with pytest.raises(TypeError):
        parse_pulse({"pulse": "bad"})


def test_pulse_config_to_dict_roundtrip():
    cfg = PulseConfig(enabled=True, interval_seconds=20, channel="stderr", message="hi")
    d = pulse_config_to_dict(cfg)
    assert d["enabled"] is True
    assert d["interval_seconds"] == 20
    assert d["channel"] == "stderr"
    assert d["message"] == "hi"


def test_make_emitter_returns_emitter():
    cfg = PulseConfig(enabled=True)
    emitter = make_emitter(cfg)
    assert isinstance(emitter, PulseEmitter)
    assert emitter.config is cfg


def test_describe_middleware_delegates():
    cfg = PulseConfig()
    assert describe(cfg) == describe_pulse(cfg)
