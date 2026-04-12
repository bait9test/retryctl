"""Tests for retryctl.signal_handler and retryctl.signal_middleware."""
from __future__ import annotations

import signal
import pytest

from retryctl.signal_handler import SignalConfig, SignalHandler, SignalInterrupted
from retryctl.signal_middleware import (
    parse_signal,
    signal_config_to_dict,
    run_with_signal_guard,
    describe_signal,
)


# ---------------------------------------------------------------------------
# SignalConfig
# ---------------------------------------------------------------------------

def test_config_defaults():
    cfg = SignalConfig()
    assert cfg.handle_sigint is True
    assert cfg.handle_sigterm is True
    assert cfg.propagate is True


def test_config_from_dict_full():
    cfg = SignalConfig.from_dict({"handle_sigint": False, "handle_sigterm": False, "propagate": False})
    assert cfg.handle_sigint is False
    assert cfg.handle_sigterm is False
    assert cfg.propagate is False


def test_config_from_dict_empty():
    cfg = SignalConfig.from_dict({})
    assert cfg.handle_sigint is True


def test_config_from_dict_invalid_type_raises():
    with pytest.raises(TypeError):
        SignalConfig.from_dict("bad")


# ---------------------------------------------------------------------------
# SignalHandler
# ---------------------------------------------------------------------------

def test_handler_not_interrupted_initially():
    cfg = SignalConfig()
    h = SignalHandler(config=cfg)
    assert h.interrupted is False
    assert h.signum is None


def test_handler_flags_interrupt_on_signal():
    cfg = SignalConfig()
    h = SignalHandler(config=cfg)
    h._handle(signal.SIGINT, None)
    assert h.interrupted is True
    assert h.signum == signal.SIGINT


def test_raise_if_interrupted_raises():
    cfg = SignalConfig()
    h = SignalHandler(config=cfg)
    h._handle(signal.SIGTERM, None)
    with pytest.raises(SignalInterrupted) as exc_info:
        h.raise_if_interrupted()
    assert exc_info.value.signum == signal.SIGTERM


def test_raise_if_not_interrupted_does_nothing():
    cfg = SignalConfig()
    h = SignalHandler(config=cfg)
    h.raise_if_interrupted()  # should not raise


def test_context_manager_restores_handlers():
    original_sigint = signal.getsignal(signal.SIGINT)
    cfg = SignalConfig(handle_sigint=True, handle_sigterm=False)
    with SignalHandler(config=cfg):
        pass
    assert signal.getsignal(signal.SIGINT) == original_sigint


# ---------------------------------------------------------------------------
# Middleware helpers
# ---------------------------------------------------------------------------

def test_parse_signal_empty_config():
    cfg = parse_signal({})
    assert cfg.handle_sigint is True


def test_parse_signal_section():
    cfg = parse_signal({"signal": {"handle_sigint": False}})
    assert cfg.handle_sigint is False


def test_parse_signal_invalid_section_raises():
    with pytest.raises(TypeError):
        parse_signal({"signal": "bad"})


def test_signal_config_to_dict_roundtrip():
    cfg = SignalConfig(handle_sigint=False, handle_sigterm=True, propagate=False)
    d = signal_config_to_dict(cfg)
    assert d == {"handle_sigint": False, "handle_sigterm": True, "propagate": False}


def test_run_with_signal_guard_returns_value():
    cfg = SignalConfig()
    result = run_with_signal_guard(cfg, lambda: 42)
    assert result == 42


def test_run_with_signal_guard_propagates_exception():
    cfg = SignalConfig()
    with pytest.raises(ValueError):
        run_with_signal_guard(cfg, lambda: (_ for _ in ()).throw(ValueError("boom")))


def test_describe_signal_both():
    cfg = SignalConfig()
    desc = describe_signal(cfg)
    assert "SIGINT" in desc
    assert "SIGTERM" in desc


def test_describe_signal_disabled():
    cfg = SignalConfig(handle_sigint=False, handle_sigterm=False)
    assert describe_signal(cfg) == "signal handling disabled"


def test_describe_signal_propagate_shown():
    cfg = SignalConfig(propagate=False)
    assert "propagate=no" in describe_signal(cfg)
