"""Middleware helpers that wire CircuitBreaker into the retry pipeline."""
from __future__ import annotations

from typing import Any

from retryctl.circuit import CircuitConfig, check_circuit, record_failure, record_success


def parse_circuit(raw_config: dict) -> CircuitConfig:
    """Extract and validate the [circuit] section from the top-level config dict."""
    section = raw_config.get("circuit", {})
    if not isinstance(section, dict):
        raise TypeError("[circuit] must be a TOML table")
    return CircuitConfig.from_dict(section)


def circuit_config_to_dict(cfg: CircuitConfig) -> dict:
    """Serialise a CircuitConfig back to a plain dict (for state persistence)."""
    return {
        "enabled": cfg.enabled,
        "failure_threshold": cfg.failure_threshold,
        "reset_seconds": cfg.reset_seconds,
        "state_dir": cfg.state_dir,
    }


def enforce_circuit_gate(cfg: CircuitConfig, key: str) -> None:
    """Call before each attempt.  Raises CircuitOpen when the circuit is open."""
    check_circuit(cfg, key)


def on_attempt_failure(cfg: CircuitConfig, key: str) -> None:
    """Call after a failed attempt to update the failure counter."""
    record_failure(cfg, key)


def on_run_success(cfg: CircuitConfig, key: str) -> None:
    """Call after the command eventually succeeds to reset the circuit."""
    record_success(cfg, key)
