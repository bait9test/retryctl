"""Tests for retryctl/pivot.py."""
import pytest
from retryctl.pivot import PivotConfig, PivotState, resolve_command


# ---------------------------------------------------------------------------
# PivotConfig.from_dict
# ---------------------------------------------------------------------------

def test_from_dict_defaults():
    cfg = PivotConfig.from_dict({})
    assert cfg.enabled is False
    assert cfg.threshold == 3
    assert cfg.command == []
    assert cfg.reset_on_success is True


def test_from_dict_full():
    cfg = PivotConfig.from_dict(
        {"command": ["fallback", "--safe"], "threshold": 2, "reset_on_success": False}
    )
    assert cfg.enabled is True
    assert cfg.threshold == 2
    assert cfg.command == ["fallback", "--safe"]
    assert cfg.reset_on_success is False


def test_from_dict_string_command_splits():
    cfg = PivotConfig.from_dict({"command": "fallback --safe"})
    assert cfg.command == ["fallback", "--safe"]


def test_from_dict_auto_enables_when_command_set():
    cfg = PivotConfig.from_dict({"command": ["alt-cmd"]})
    assert cfg.enabled is True


def test_from_dict_explicit_disabled_overrides_command():
    cfg = PivotConfig.from_dict({"command": ["alt-cmd"], "enabled": False})
    assert cfg.enabled is False


def test_from_dict_invalid_type_raises():
    with pytest.raises(TypeError):
        PivotConfig.from_dict("not a dict")


def test_from_dict_invalid_command_type_raises():
    with pytest.raises(TypeError):
        PivotConfig.from_dict({"command": 123})


def test_from_dict_zero_threshold_raises():
    with pytest.raises(ValueError):
        PivotConfig.from_dict({"command": ["x"], "threshold": 0})


# ---------------------------------------------------------------------------
# PivotState
# ---------------------------------------------------------------------------

def test_initial_state():
    s = PivotState()
    assert s.consecutive_failures == 0
    assert s.pivoted is False


def test_record_failure_increments():
    s = PivotState()
    s.record_failure()
    s.record_failure()
    assert s.consecutive_failures == 2


def test_record_success_resets_when_configured():
    cfg = PivotConfig(enabled=True, threshold=2, command=["x"], reset_on_success=True)
    s = PivotState(consecutive_failures=5, pivoted=True)
    s.record_success(cfg)
    assert s.consecutive_failures == 0
    assert s.pivoted is False


def test_record_success_no_reset_when_disabled():
    cfg = PivotConfig(enabled=True, threshold=2, command=["x"], reset_on_success=False)
    s = PivotState(consecutive_failures=5, pivoted=True)
    s.record_success(cfg)
    assert s.consecutive_failures == 5
    assert s.pivoted is True


def test_should_pivot_below_threshold():
    cfg = PivotConfig(enabled=True, threshold=3, command=["x"])
    s = PivotState(consecutive_failures=2)
    assert s.should_pivot(cfg) is False


def test_should_pivot_at_threshold():
    cfg = PivotConfig(enabled=True, threshold=3, command=["x"])
    s = PivotState(consecutive_failures=3)
    assert s.should_pivot(cfg) is True


# ---------------------------------------------------------------------------
# resolve_command
# ---------------------------------------------------------------------------

def test_resolve_returns_original_when_disabled():
    cfg = PivotConfig(enabled=False, threshold=1, command=["alt"])
    s = PivotState(consecutive_failures=10)
    assert resolve_command(cfg, s, ["original"]) == ["original"]


def test_resolve_returns_original_below_threshold():
    cfg = PivotConfig(enabled=True, threshold=3, command=["alt"])
    s = PivotState(consecutive_failures=2)
    assert resolve_command(cfg, s, ["original"]) == ["original"]


def test_resolve_returns_pivot_at_threshold():
    cfg = PivotConfig(enabled=True, threshold=3, command=["alt"])
    s = PivotState(consecutive_failures=3)
    assert resolve_command(cfg, s, ["original"]) == ["alt"]


def test_resolve_sets_pivoted_flag(caplog):
    import logging
    cfg = PivotConfig(enabled=True, threshold=2, command=["alt"])
    s = PivotState(consecutive_failures=2)
    with caplog.at_level(logging.WARNING, logger="retryctl.pivot"):
        resolve_command(cfg, s, ["original"])
    assert s.pivoted is True
    assert "pivot command" in caplog.text
