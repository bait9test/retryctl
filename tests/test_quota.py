"""Unit tests for retryctl.quota."""
from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from retryctl.quota import (
    QuotaConfig,
    QuotaExceeded,
    _quota_file,
    _sanitise_key,
    check_quota,
    record_retry,
    reset_quota,
)


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def test_config_defaults():
    cfg = QuotaConfig()
    assert cfg.enabled is False
    assert cfg.max_retries == 0
    assert cfg.window_seconds == 3600
    assert cfg.key is None


def test_config_from_dict_full():
    cfg = QuotaConfig.from_dict(
        {"enabled": True, "max_retries": 5, "window_seconds": 600, "key": "myjob"}
    )
    assert cfg.enabled is True
    assert cfg.max_retries == 5
    assert cfg.window_seconds == 600
    assert cfg.key == "myjob"


def test_config_from_dict_empty():
    cfg = QuotaConfig.from_dict({})
    assert cfg.enabled is False


# ---------------------------------------------------------------------------
# Key sanitisation
# ---------------------------------------------------------------------------

def test_sanitise_key_replaces_spaces():
    assert _sanitise_key("my command") == "my_command"


def test_sanitise_key_truncates_long_keys():
    assert len(_sanitise_key("a" * 200)) == 64


def test_sanitise_key_preserves_alphanumeric():
    assert _sanitise_key("abc-123_XYZ") == "abc-123_XYZ"


# ---------------------------------------------------------------------------
# check_quota / record_retry / reset_quota
# ---------------------------------------------------------------------------

def test_disabled_quota_always_allows(tmp_path):
    cfg = QuotaConfig(enabled=False, max_retries=1, state_dir=str(tmp_path))
    assert check_quota(cfg, "cmd") == 0


def test_zero_max_retries_always_allows(tmp_path):
    cfg = QuotaConfig(enabled=True, max_retries=0, state_dir=str(tmp_path))
    assert check_quota(cfg, "cmd") == 0


def test_allows_up_to_limit(tmp_path):
    cfg = QuotaConfig(enabled=True, max_retries=3, window_seconds=60, state_dir=str(tmp_path))
    for _ in range(3):
        record_retry(cfg, "cmd")
    with pytest.raises(QuotaExceeded) as exc_info:
        check_quota(cfg, "cmd")
    assert exc_info.value.used == 3
    assert exc_info.value.limit == 3


def test_record_retry_creates_file(tmp_path):
    cfg = QuotaConfig(enabled=True, max_retries=5, window_seconds=60, state_dir=str(tmp_path))
    record_retry(cfg, "cmd")
    path = _quota_file(cfg, "cmd")
    assert path.exists()
    data = json.loads(path.read_text())
    assert len(data["timestamps"]) == 1


def test_expired_timestamps_evicted(tmp_path):
    cfg = QuotaConfig(enabled=True, max_retries=2, window_seconds=1, state_dir=str(tmp_path))
    path = _quota_file(cfg, "cmd")
    path.parent.mkdir(parents=True, exist_ok=True)
    old_ts = time.time() - 10
    path.write_text(json.dumps({"timestamps": [old_ts]}))
    # old entry should be evicted — quota should not be exceeded
    assert check_quota(cfg, "cmd") == 0


def test_reset_quota_removes_file(tmp_path):
    cfg = QuotaConfig(enabled=True, max_retries=5, window_seconds=60, state_dir=str(tmp_path))
    record_retry(cfg, "cmd")
    reset_quota(cfg, "cmd")
    assert not _quota_file(cfg, "cmd").exists()


def test_reset_quota_disabled_is_noop(tmp_path):
    cfg = QuotaConfig(enabled=False, state_dir=str(tmp_path))
    # Should not raise even if file doesn't exist
    reset_quota(cfg, "cmd")


def test_quota_exceeded_message():
    exc = QuotaExceeded(5, 5, 3600)
    assert "5/5" in str(exc)
    assert "3600" in str(exc)
