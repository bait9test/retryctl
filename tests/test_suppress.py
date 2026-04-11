"""Tests for retryctl.suppress and retryctl.suppress_middleware."""
import pytest

from retryctl.suppress import (
    SuppressConfig,
    from_dict,
    is_suppressed,
    suppress_config_to_dict,
)
from retryctl.suppress_middleware import (
    check_suppress_gate,
    parse_suppress,
    suppress_config_summary,
)


# ---------------------------------------------------------------------------
# from_dict
# ---------------------------------------------------------------------------

def test_from_dict_defaults():
    cfg = from_dict({})
    assert cfg.enabled is False
    assert cfg.exit_codes == []
    assert cfg.stdout_patterns == []
    assert cfg.stderr_patterns == []


def test_from_dict_exit_codes_auto_enables():
    cfg = from_dict({"exit_codes": [1, 2]})
    assert cfg.enabled is True
    assert cfg.exit_codes == [1, 2]


def test_from_dict_patterns_auto_enable():
    cfg = from_dict({"stdout_patterns": ["transient"]})
    assert cfg.enabled is True


def test_from_dict_explicit_disabled_overrides():
    cfg = from_dict({"enabled": False, "exit_codes": [1]})
    assert cfg.enabled is False


def test_from_dict_invalid_type_raises():
    with pytest.raises(TypeError):
        from_dict("not-a-dict")


def test_from_dict_exit_codes_not_list_raises():
    with pytest.raises(TypeError):
        from_dict({"exit_codes": 42})


# ---------------------------------------------------------------------------
# is_suppressed
# ---------------------------------------------------------------------------

def test_disabled_config_never_suppresses():
    cfg = SuppressConfig(enabled=False, exit_codes=[0, 1, 2])
    assert is_suppressed(cfg, 1) is False


def test_exit_code_match_suppresses():
    cfg = from_dict({"exit_codes": [3, 42]})
    assert is_suppressed(cfg, 42) is True


def test_exit_code_no_match_not_suppressed():
    cfg = from_dict({"exit_codes": [3]})
    assert is_suppressed(cfg, 1) is False


def test_stdout_pattern_match_suppresses():
    cfg = from_dict({"stdout_patterns": [r"rate.?limit"]})
    assert is_suppressed(cfg, 1, stdout="hit rate-limit") is True


def test_stderr_pattern_match_suppresses():
    cfg = from_dict({"stderr_patterns": ["temporary"]})
    assert is_suppressed(cfg, 1, stderr="temporary error") is True


def test_no_matching_pattern_not_suppressed():
    cfg = from_dict({"stdout_patterns": ["transient"]})
    assert is_suppressed(cfg, 1, stdout="permanent failure") is False


# ---------------------------------------------------------------------------
# suppress_config_to_dict
# ---------------------------------------------------------------------------

def test_roundtrip_via_dict():
    original = from_dict({"exit_codes": [1], "stderr_patterns": ["oops"]})
    d = suppress_config_to_dict(original)
    restored = from_dict(d)
    assert restored.exit_codes == [1]
    assert restored.stderr_patterns == ["oops"]


# ---------------------------------------------------------------------------
# middleware helpers
# ---------------------------------------------------------------------------

def test_parse_suppress_missing_section_uses_defaults():
    cfg = parse_suppress({})
    assert cfg.enabled is False


def test_parse_suppress_full_section():
    cfg = parse_suppress({"suppress": {"exit_codes": [5]}})
    assert 5 in cfg.exit_codes


def test_parse_suppress_invalid_type_raises():
    with pytest.raises(TypeError):
        parse_suppress({"suppress": "bad"})


def test_check_suppress_gate_returns_true_when_suppressed():
    cfg = from_dict({"exit_codes": [99]})
    assert check_suppress_gate(cfg, 99) is True


def test_check_suppress_gate_returns_false_when_not_suppressed():
    cfg = from_dict({"exit_codes": [99]})
    assert check_suppress_gate(cfg, 1) is False


def test_suppress_config_summary_disabled():
    cfg = SuppressConfig()
    assert "disabled" in suppress_config_summary(cfg)


def test_suppress_config_summary_with_rules():
    cfg = from_dict({"exit_codes": [1, 2], "stdout_patterns": ["retry"]})
    summary = suppress_config_summary(cfg)
    assert "exit_codes" in summary
    assert "stdout_patterns" in summary
