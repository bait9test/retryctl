"""Middleware helpers for wiring SignalHandler into the retry loop."""
from __future__ import annotations

import logging
from typing import Any

from retryctl.signal_handler import SignalConfig, SignalHandler, SignalInterrupted

log = logging.getLogger(__name__)


def parse_signal(config_dict: dict) -> SignalConfig:
    """Extract [signal] section from top-level config dict."""
    raw = config_dict.get("signal", {})
    if not isinstance(raw, dict):
        raise TypeError(f"[signal] must be a table, got {type(raw).__name__}")
    return SignalConfig.from_dict(raw)


def signal_config_to_dict(cfg: SignalConfig) -> dict:
    """Serialise SignalConfig back to a plain dict."""
    return {
        "handle_sigint": cfg.handle_sigint,
        "handle_sigterm": cfg.handle_sigterm,
        "propagate": cfg.propagate,
    }


def run_with_signal_guard(cfg: SignalConfig, fn, *args, **kwargs) -> Any:
    """
    Run *fn* inside a SignalHandler context.

    If a signal arrives the handler flags the interrupt; after *fn* returns
    (or raises) we call raise_if_interrupted so the caller sees
    SignalInterrupted rather than a silent exit.
    """
    handler = SignalHandler(config=cfg)
    with handler:
        try:
            result = fn(*args, **kwargs)
        except SignalInterrupted:
            raise
        except Exception:
            handler.raise_if_interrupted()
            raise
        handler.raise_if_interrupted()
        return result


def describe_signal(cfg: SignalConfig) -> str:
    """Human-readable summary for CLI --describe output."""
    parts = []
    if cfg.handle_sigint:
        parts.append("SIGINT")
    if cfg.handle_sigterm:
        parts.append("SIGTERM")
    if not parts:
        return "signal handling disabled"
    propagate = "propagate=yes" if cfg.propagate else "propagate=no"
    return f"handling {', '.join(parts)} ({propagate})"
