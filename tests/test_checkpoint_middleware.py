"""Integration-style tests for checkpoint_middleware."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from retryctl.backoff import BackoffConfig, BackoffStrategy
from retryctl.checkpoint import CheckpointConfig, CheckpointData, load_checkpoint, save_checkpoint
from retryctl.checkpoint_middleware import run_with_checkpoint
from retryctl.runner import RetryResult


@pytest.fixture()
def cfg(tmp_path: Path) -> CheckpointConfig:
    return CheckpointConfig(enabled=True, directory=str(tmp_path), ttl_seconds=3600)


@pytest.fixture()
def backoff() -> BackoffConfig:
    return BackoffConfig(strategy=BackoffStrategy.FIXED, base_delay=0.0, jitter=False)


def _make_result(succeeded: bool) -> RetryResult:
    r = MagicMock(spec=RetryResult)
    r.succeeded = succeeded
    return r


def test_clears_checkpoint_on_success(cfg, backoff):
    with patch("retryctl.checkpoint_middleware.run_with_retry", return_value=_make_result(True)) as mock_run:
        run_with_checkpoint(["echo", "ok"], max_attempts=3, backoff_cfg=backoff, checkpoint_cfg=cfg)
    assert load_checkpoint(cfg, "echo ok") is None


def test_clears_checkpoint_on_failure(cfg, backoff):
    with patch("retryctl.checkpoint_middleware.run_with_retry", return_value=_make_result(False)):
        run_with_checkpoint(["false"], max_attempts=3, backoff_cfg=backoff, checkpoint_cfg=cfg)
    assert load_checkpoint(cfg, "false") is None


def test_reduces_attempts_when_checkpoint_exists(cfg, backoff):
    save_checkpoint(cfg, CheckpointData(command="my cmd", attempt=2))
    captured = {}

    def fake_run(command, max_attempts, backoff_cfg, shell=False, attempt_callback=None):
        captured["max_attempts"] = max_attempts
        return _make_result(True)

    with patch("retryctl.checkpoint_middleware.run_with_retry", side_effect=fake_run):
        run_with_checkpoint(["my", "cmd"], max_attempts=5, backoff_cfg=backoff, checkpoint_cfg=cfg)

    assert captured["max_attempts"] == 3  # 5 - 2


def test_resets_if_checkpoint_exceeds_max(cfg, backoff):
    save_checkpoint(cfg, CheckpointData(command="cmd", attempt=99))
    captured = {}

    def fake_run(command, max_attempts, backoff_cfg, shell=False, attempt_callback=None):
        captured["max_attempts"] = max_attempts
        return _make_result(True)

    with patch("retryctl.checkpoint_middleware.run_with_retry", side_effect=fake_run):
        run_with_checkpoint(["cmd"], max_attempts=3, backoff_cfg=backoff, checkpoint_cfg=cfg)

    assert captured["max_attempts"] == 3


def test_no_checkpoint_uses_full_attempts(cfg, backoff):
    captured = {}

    def fake_run(command, max_attempts, backoff_cfg, shell=False, attempt_callback=None):
        captured["max_attempts"] = max_attempts
        return _make_result(True)

    with patch("retryctl.checkpoint_middleware.run_with_retry", side_effect=fake_run):
        run_with_checkpoint(["cmd"], max_attempts=4, backoff_cfg=backoff, checkpoint_cfg=cfg)

    assert captured["max_attempts"] == 4
