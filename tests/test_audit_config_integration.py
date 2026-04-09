"""Integration-style tests: AuditConfig round-trips through config.py parsing."""

from __future__ import annotations

import pytest

from retryctl.audit import AuditConfig, _DEFAULT_AUDIT_FILE


def _parse(data: dict) -> AuditConfig:
    """Simulate what config.py would do with the [audit] table."""
    return AuditConfig.from_dict(data)


def test_from_dict_all_fields():
    cfg = _parse({"enabled": True, "audit_file": "/var/log/retryctl/audit.jsonl"})
    assert cfg.enabled is True
    assert cfg.audit_file == "/var/log/retryctl/audit.jsonl"


def test_from_dict_enabled_coerced_to_bool():
    cfg = _parse({"enabled": 1})
    assert cfg.enabled is True


def test_from_dict_missing_file_uses_default():
    cfg = _parse({"enabled": True})
    assert cfg.audit_file == _DEFAULT_AUDIT_FILE


def test_from_dict_extra_keys_ignored():
    cfg = _parse({"enabled": False, "unknown_key": "value"})
    assert cfg.enabled is False


def test_repr_contains_key_info():
    cfg = AuditConfig(enabled=True, audit_file="/tmp/a.jsonl")
    r = repr(cfg)
    assert "True" in r
    assert "/tmp/a.jsonl" in r
