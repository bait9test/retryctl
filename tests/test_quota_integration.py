"""Integration-style tests: quota interacting with multiple retries."""
from __future__ import annotations

import pytest

from retryctl.quota import (
    QuotaConfig,
    QuotaExceeded,
    check_quota,
    record_retry,
    reset_quota,
)


def _make_cfg(tmp_path, max_retries: int = 3, window: int = 60) -> QuotaConfig:
    return QuotaConfig(
        enabled=True,
        max_retries=max_retries,
        window_seconds=window,
        state_dir=str(tmp_path),
    )


def test_full_retry_loop_exhausts_quota(tmp_path):
    cfg = _make_cfg(tmp_path, max_retries=3)
    for _ in range(3):
        check_quota(cfg, "failing-cmd")  # should pass
        record_retry(cfg, "failing-cmd")
    with pytest.raises(QuotaExceeded) as exc_info:
        check_quota(cfg, "failing-cmd")
    assert exc_info.value.used == 3
    assert exc_info.value.limit == 3


def test_quota_not_consumed_on_success(tmp_path):
    cfg = _make_cfg(tmp_path, max_retries=3)
    # Simulate a run that succeeds on first try — no record_retry called
    check_quota(cfg, "ok-cmd")
    reset_quota(cfg, "ok-cmd")
    assert check_quota(cfg, "ok-cmd") == 0


def test_disabled_quota_never_raises(tmp_path):
    cfg = QuotaConfig(enabled=False, max_retries=1, state_dir=str(tmp_path))
    for _ in range(100):
        record_retry(cfg, "cmd")  # no-op
    check_quota(cfg, "cmd")  # should not raise


def test_quota_exceeded_error_message(tmp_path):
    cfg = _make_cfg(tmp_path, max_retries=2, window=120)
    record_retry(cfg, "cmd")
    record_retry(cfg, "cmd")
    with pytest.raises(QuotaExceeded) as exc_info:
        check_quota(cfg, "cmd")
    msg = str(exc_info.value)
    assert "2/2" in msg
    assert "120" in msg


def test_separate_commands_have_independent_quotas(tmp_path):
    cfg = _make_cfg(tmp_path, max_retries=1)
    record_retry(cfg, "cmd-a")
    # cmd-b should be unaffected
    assert check_quota(cfg, "cmd-b") == 0
    with pytest.raises(QuotaExceeded):
        check_quota(cfg, "cmd-a")
