"""Tests for retryctl.quota_middleware."""
from __future__ import annotations

import pytest

from retryctl.quota import QuotaConfig, QuotaExceeded, record_retry
from retryctl.quota_middleware import (
    enforce_quota_gate,
    on_retry_consumed,
    on_run_success,
    parse_quota,
    quota_config_to_dict,
)


def test_parse_quota_empty_config():
    cfg = parse_quota({})
    assert isinstance(cfg, QuotaConfig)
    assert cfg.enabled is False


def test_parse_quota_full_section():
    raw = {"quota": {"enabled": True, "max_retries": 10, "window_seconds": 300}}
    cfg = parse_quota(raw)
    assert cfg.enabled is True
    assert cfg.max_retries == 10


def test_parse_quota_missing_section_uses_defaults():
    cfg = parse_quota({"other": "stuff"})
    assert cfg.enabled is False


def test_parse_quota_invalid_type_raises():
    with pytest.raises(TypeError):
        parse_quota({"quota": "not-a-table"})


def test_quota_config_to_dict_roundtrip():
    cfg = QuotaConfig(enabled=True, max_retries=7, window_seconds=900, key="k")
    d = quota_config_to_dict(cfg)
    restored = QuotaConfig.from_dict(d)
    assert restored.enabled == cfg.enabled
    assert restored.max_retries == cfg.max_retries
    assert restored.window_seconds == cfg.window_seconds
    assert restored.key == cfg.key


def test_enforce_quota_gate_passes_when_disabled(tmp_path):
    cfg = QuotaConfig(enabled=False, max_retries=1, state_dir=str(tmp_path))
    enforce_quota_gate(cfg, "cmd")  # should not raise


def test_enforce_quota_gate_raises_when_exceeded(tmp_path):
    cfg = QuotaConfig(enabled=True, max_retries=2, window_seconds=60, state_dir=str(tmp_path))
    record_retry(cfg, "cmd")
    record_retry(cfg, "cmd")
    with pytest.raises(QuotaExceeded):
        enforce_quota_gate(cfg, "cmd")


def test_on_retry_consumed_records(tmp_path):
    cfg = QuotaConfig(enabled=True, max_retries=5, window_seconds=60, state_dir=str(tmp_path))
    on_retry_consumed(cfg, "cmd")
    on_retry_consumed(cfg, "cmd")
    from retryctl.quota import check_quota
    assert check_quota(cfg, "cmd") == 2


def test_on_run_success_resets(tmp_path):
    cfg = QuotaConfig(enabled=True, max_retries=5, window_seconds=60, state_dir=str(tmp_path))
    record_retry(cfg, "cmd")
    on_run_success(cfg, "cmd")
    from retryctl.quota import check_quota
    assert check_quota(cfg, "cmd") == 0
