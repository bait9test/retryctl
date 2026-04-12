"""Integration-style tests that wire fallback through the middleware layer."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from retryctl.fallback import FallbackConfig
from retryctl.fallback_middleware import maybe_run_fallback, parse_fallback


def _make_metrics(succeeded: bool) -> MagicMock:
    m = MagicMock()
    m.succeeded = succeeded
    return m


def test_full_failure_triggers_fallback():
    """End-to-end: failed run → fallback runs → result captured."""
    raw = {"fallback": {"command": ["echo", "alert"], "timeout": 2.0}}
    cfg = parse_fallback(raw)
    metrics = _make_metrics(succeeded=False)

    mock_proc = MagicMock(returncode=0, stdout="alert\n", stderr="")
    with patch("subprocess.run", return_value=mock_proc) as mock_run:
        result = maybe_run_fallback(cfg, metrics)

    mock_run.assert_called_once()
    assert result.ran is True
    assert result.exit_code == 0
    assert result.stdout == "alert\n"


def test_success_skips_fallback():
    """Successful run must never invoke the fallback subprocess."""
    raw = {"fallback": {"command": ["echo", "alert"]}}
    cfg = parse_fallback(raw)
    metrics = _make_metrics(succeeded=True)

    with patch("subprocess.run") as mock_run:
        result = maybe_run_fallback(cfg, metrics)

    mock_run.assert_not_called()
    assert result.ran is False


def test_disabled_fallback_never_runs_even_on_failure():
    cfg = FallbackConfig(enabled=False, command=["echo", "hi"])
    metrics = _make_metrics(succeeded=False)

    with patch("subprocess.run") as mock_run:
        result = maybe_run_fallback(cfg, metrics)

    mock_run.assert_not_called()
    assert result.ran is False


def test_fallback_nonzero_does_not_raise():
    """A non-zero fallback exit should be tolerated (logged, not raised)."""
    cfg = FallbackConfig(enabled=True, command=["false"])
    metrics = _make_metrics(succeeded=False)

    mock_proc = MagicMock(returncode=1, stdout="", stderr="fail")
    with patch("subprocess.run", return_value=mock_proc):
        result = maybe_run_fallback(cfg, metrics)  # must not raise

    assert result.ran is True
    assert result.exit_code == 1


def test_fallback_error_message_contains_stderr():
    cfg = FallbackConfig(enabled=True, command=["bad-cmd"])
    metrics = _make_metrics(succeeded=False)

    with patch("subprocess.run", side_effect=FileNotFoundError("bad-cmd not found")):
        result = maybe_run_fallback(cfg, metrics)

    assert "bad-cmd not found" in result.stderr
