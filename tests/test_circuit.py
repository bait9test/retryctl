"""Unit tests for retryctl.circuit and retryctl.circuit_middleware."""
from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from retryctl.circuit import (
    CircuitConfig,
    CircuitOpen,
    _sanitise_key,
    _state_path,
    check_circuit,
    record_failure,
    record_success,
)
from retryctl.circuit_middleware import (
    circuit_config_to_dict,
    enforce_circuit_gate,
    on_attempt_failure,
    on_run_success,
    parse_circuit,
)


# ---------------------------------------------------------------------------
# CircuitConfig
# ---------------------------------------------------------------------------

def test_config_defaults():
    cfg = CircuitConfig()
    assert cfg.enabled is False
    assert cfg.failure_threshold == 5
    assert cfg.reset_seconds == 60


def test_config_from_dict_full():
    cfg = CircuitConfig.from_dict(
        {"enabled": True, "failure_threshold": 3, "reset_seconds": 30, "state_dir": "/tmp/x"}
    )
    assert cfg.enabled is True
    assert cfg.failure_threshold == 3
    assert cfg.reset_seconds == 30
    assert cfg.state_dir == "/tmp/x"


def test_config_from_dict_empty():
    cfg = CircuitConfig.from_dict({})
    assert cfg.enabled is False


def test_config_invalid_threshold_raises():
    with pytest.raises(ValueError, match="failure_threshold"):
        CircuitConfig.from_dict({"failure_threshold": 0})


def test_config_negative_reset_raises():
    with pytest.raises(ValueError, match="reset_seconds"):
        CircuitConfig.from_dict({"reset_seconds": -1})


def test_config_wrong_type_raises():
    with pytest.raises(TypeError):
        CircuitConfig.from_dict("not a dict")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# _sanitise_key
# ---------------------------------------------------------------------------

def test_sanitise_key_replaces_spaces():
    assert " " not in _sanitise_key("my command")


def test_sanitise_key_truncates():
    assert len(_sanitise_key("x" * 100)) == 64


# ---------------------------------------------------------------------------
# check_circuit / record_failure / record_success
# ---------------------------------------------------------------------------

@pytest.fixture()
def tmp_cfg(tmp_path):
    return CircuitConfig(
        enabled=True, failure_threshold=3, reset_seconds=60, state_dir=str(tmp_path)
    )


def test_disabled_always_passes(tmp_cfg):
    cfg = CircuitConfig(enabled=False)
    for _ in range(10):
        record_failure(cfg, "cmd")
    check_circuit(cfg, "cmd")  # should not raise


def test_circuit_opens_after_threshold(tmp_cfg):
    for _ in range(3):
        record_failure(tmp_cfg, "cmd")
    with pytest.raises(CircuitOpen):
        check_circuit(tmp_cfg, "cmd")


def test_circuit_stays_closed_below_threshold(tmp_cfg):
    record_failure(tmp_cfg, "cmd")
    record_failure(tmp_cfg, "cmd")
    check_circuit(tmp_cfg, "cmd")  # only 2 failures, threshold=3 → should pass


def test_circuit_resets_on_success(tmp_cfg):
    for _ in range(3):
        record_failure(tmp_cfg, "cmd")
    record_success(tmp_cfg, "cmd")
    check_circuit(tmp_cfg, "cmd")  # should not raise after reset


def test_circuit_resets_after_window(tmp_cfg, tmp_path):
    tmp_cfg.reset_seconds = 0
    for _ in range(3):
        record_failure(tmp_cfg, "cmd")
    time.sleep(0.01)
    check_circuit(tmp_cfg, "cmd")  # window expired → should pass


def test_circuit_open_error_message(tmp_cfg):
    for _ in range(3):
        record_failure(tmp_cfg, "cmd")
    with pytest.raises(CircuitOpen) as exc_info:
        check_circuit(tmp_cfg, "cmd")
    assert "cmd" in str(exc_info.value)


# ---------------------------------------------------------------------------
# circuit_middleware
# ---------------------------------------------------------------------------

def test_parse_circuit_empty_config():
    cfg = parse_circuit({})
    assert cfg.enabled is False


def test_parse_circuit_full_section():
    cfg = parse_circuit({"circuit": {"enabled": True, "failure_threshold": 2}})
    assert cfg.enabled is True
    assert cfg.failure_threshold == 2


def test_parse_circuit_invalid_type_raises():
    with pytest.raises(TypeError):
        parse_circuit({"circuit": "bad"})


def test_circuit_config_to_dict_roundtrip():
    original = CircuitConfig(enabled=True, failure_threshold=4, reset_seconds=45)
    d = circuit_config_to_dict(original)
    restored = CircuitConfig.from_dict(d)
    assert restored.enabled == original.enabled
    assert restored.failure_threshold == original.failure_threshold
    assert restored.reset_seconds == original.reset_seconds


def test_enforce_gate_raises_when_open(tmp_cfg):
    for _ in range(3):
        on_attempt_failure(tmp_cfg, "key")
    with pytest.raises(CircuitOpen):
        enforce_circuit_gate(tmp_cfg, "key")


def test_on_run_success_resets(tmp_cfg):
    for _ in range(3):
        on_attempt_failure(tmp_cfg, "key")
    on_run_success(tmp_cfg, "key")
    enforce_circuit_gate(tmp_cfg, "key")  # should not raise
