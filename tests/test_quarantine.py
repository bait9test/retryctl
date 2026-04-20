"""Tests for retryctl.quarantine and retryctl.quarantine_middleware."""
from __future__ import annotations

import time
import pytest

from retryctl.quarantine import (
    QuarantineConfig,
    QuarantineBlocked,
    _registry,
    check_quarantine,
    record_failure,
    record_success,
)
from retryctl.quarantine_middleware import (
    parse_quarantine,
    quarantine_config_to_dict,
    before_attempt,
    on_attempt_failure,
    on_run_success,
    describe_quarantine,
)


@pytest.fixture(autouse=True)
def clear_registry():
    _registry.clear()
    yield
    _registry.clear()


# --- QuarantineConfig ---

def test_config_defaults():
    cfg = QuarantineConfig()
    assert cfg.enabled is False
    assert cfg.threshold == 5
    assert cfg.window_seconds == 60.0
    assert cfg.duration_seconds == 300.0
    assert cfg.key == "default"


def test_from_dict_full():
    cfg = QuarantineConfig.from_dict({
        "enabled": True,
        "threshold": 3,
        "window_seconds": 30.0,
        "duration_seconds": 120.0,
        "key": "my-job",
    })
    assert cfg.enabled is True
    assert cfg.threshold == 3
    assert cfg.window_seconds == 30.0
    assert cfg.duration_seconds == 120.0
    assert cfg.key == "my-job"


def test_from_dict_empty_uses_defaults():
    cfg = QuarantineConfig.from_dict({})
    assert cfg.threshold == 5
    assert cfg.window_seconds == 60.0


def test_from_dict_invalid_type_raises():
    with pytest.raises(TypeError):
        QuarantineConfig.from_dict("bad")


def test_from_dict_zero_threshold_raises():
    with pytest.raises(ValueError):
        QuarantineConfig.from_dict({"threshold": 0})


def test_from_dict_negative_window_raises():
    with pytest.raises(ValueError):
        QuarantineConfig.from_dict({"window_seconds": -1})


def test_from_dict_negative_duration_raises():
    with pytest.raises(ValueError):
        QuarantineConfig.from_dict({"duration_seconds": 0})


# --- Core logic ---

def test_disabled_config_never_blocks():
    cfg = QuarantineConfig(enabled=False, threshold=1, window_seconds=60, duration_seconds=60, key="k")
    for _ in range(10):
        record_failure(cfg)
    check_quarantine(cfg)  # must not raise


def test_threshold_triggers_quarantine():
    cfg = QuarantineConfig(enabled=True, threshold=3, window_seconds=60, duration_seconds=60, key="q1")
    for _ in range(3):
        record_failure(cfg)
    with pytest.raises(QuarantineBlocked):
        check_quarantine(cfg)


def test_below_threshold_does_not_quarantine():
    cfg = QuarantineConfig(enabled=True, threshold=3, window_seconds=60, duration_seconds=60, key="q2")
    for _ in range(2):
        record_failure(cfg)
    check_quarantine(cfg)  # must not raise


def test_success_clears_failures():
    cfg = QuarantineConfig(enabled=True, threshold=3, window_seconds=60, duration_seconds=60, key="q3")
    for _ in range(2):
        record_failure(cfg)
    record_success(cfg)
    record_failure(cfg)  # only 1 failure now
    check_quarantine(cfg)  # must not raise


def test_quarantine_blocked_str_contains_key():
    exc = QuarantineBlocked("mykey", time.monotonic() + 100)
    assert "mykey" in str(exc)


# --- Middleware ---

def test_parse_quarantine_empty_config():
    cfg = parse_quarantine({})
    assert cfg.enabled is False


def test_parse_quarantine_full_section():
    cfg = parse_quarantine({"quarantine": {"enabled": True, "threshold": 2, "key": "x"}})
    assert cfg.enabled is True
    assert cfg.threshold == 2


def test_parse_quarantine_invalid_section_type_raises():
    with pytest.raises(TypeError):
        parse_quarantine({"quarantine": "bad"})


def test_quarantine_config_to_dict_roundtrip():
    cfg = QuarantineConfig(enabled=True, threshold=4, window_seconds=45.0, duration_seconds=200.0, key="job")
    d = quarantine_config_to_dict(cfg)
    restored = QuarantineConfig.from_dict(d)
    assert restored.threshold == 4
    assert restored.duration_seconds == 200.0


def test_before_attempt_raises_when_quarantined():
    cfg = QuarantineConfig(enabled=True, threshold=1, window_seconds=60, duration_seconds=300, key="qa")
    record_failure(cfg)
    with pytest.raises(QuarantineBlocked):
        before_attempt(cfg)


def test_on_attempt_failure_records(caplog):
    cfg = QuarantineConfig(enabled=True, threshold=5, window_seconds=60, duration_seconds=300, key="qb")
    import logging
    with caplog.at_level(logging.DEBUG, logger="retryctl.quarantine_middleware"):
        on_attempt_failure(cfg)
    assert "qb" in caplog.text


def test_on_run_success_clears(caplog):
    cfg = QuarantineConfig(enabled=True, threshold=5, window_seconds=60, duration_seconds=300, key="qc")
    import logging
    with caplog.at_level(logging.DEBUG, logger="retryctl.quarantine_middleware"):
        on_run_success(cfg)
    assert "qc" in caplog.text


def test_describe_quarantine_disabled():
    cfg = QuarantineConfig(enabled=False)
    assert "disabled" in describe_quarantine(cfg)


def test_describe_quarantine_enabled():
    cfg = QuarantineConfig(enabled=True, threshold=3, window_seconds=30, duration_seconds=120, key="z")
    desc = describe_quarantine(cfg)
    assert "z" in desc
    assert "3" in desc
