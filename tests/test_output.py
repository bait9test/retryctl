"""Tests for retryctl.output module."""

import pytest

from retryctl.output import (
    CapturedOutput,
    OutputConfig,
    OutputMode,
    format_output,
    truncate_for_alert,
)


@pytest.fixture
def captured() -> CapturedOutput:
    c = CapturedOutput()
    c.append_stdout("hello")
    c.append_stdout("world")
    c.append_stderr("warn: something")
    return c


def test_captured_output_properties(captured: CapturedOutput) -> None:
    assert captured.stdout == "hello\nworld"
    assert captured.stderr == "warn: something"


def test_format_silent_returns_none(captured: CapturedOutput) -> None:
    cfg = OutputConfig(mode=OutputMode.SILENT)
    assert format_output(captured, cfg, succeeded=False) is None


def test_format_suppressed_on_success_by_default(captured: CapturedOutput) -> None:
    cfg = OutputConfig(mode=OutputMode.CAPTURE, show_on_success=False)
    assert format_output(captured, cfg, succeeded=True) is None


def test_format_shown_on_success_when_enabled(captured: CapturedOutput) -> None:
    cfg = OutputConfig(mode=OutputMode.CAPTURE, show_on_success=True)
    result = format_output(captured, cfg, succeeded=True)
    assert result is not None
    assert "hello" in result


def test_format_shown_on_failure(captured: CapturedOutput) -> None:
    cfg = OutputConfig(mode=OutputMode.CAPTURE, show_on_failure=True)
    result = format_output(captured, cfg, succeeded=False)
    assert result is not None
    assert "[stdout]" in result
    assert "[stderr]" in result


def test_format_suppressed_on_failure_when_disabled(captured: CapturedOutput) -> None:
    cfg = OutputConfig(mode=OutputMode.CAPTURE, show_on_failure=False)
    assert format_output(captured, cfg, succeeded=False) is None


def test_format_tail_limits_lines() -> None:
    c = CapturedOutput()
    for i in range(50):
        c.append_stdout(f"line {i}")
    cfg = OutputConfig(mode=OutputMode.TAIL, tail_lines=5, show_on_failure=True)
    result = format_output(c, cfg, succeeded=False)
    assert result is not None
    lines = result.splitlines()
    # [stdout] header + 5 tail lines
    assert len(lines) == 6
    assert "line 49" in result
    assert "line 0" not in result


def test_format_prefix_applied(captured: CapturedOutput) -> None:
    cfg = OutputConfig(mode=OutputMode.CAPTURE, prefix=">> ", show_on_failure=True)
    result = format_output(captured, cfg, succeeded=False)
    assert result is not None
    for line in result.splitlines():
        assert line.startswith(">> ")


def test_format_empty_captured_returns_none() -> None:
    c = CapturedOutput()
    cfg = OutputConfig(mode=OutputMode.CAPTURE, show_on_failure=True)
    assert format_output(c, cfg, succeeded=False) is None


def test_truncate_short_text_unchanged() -> None:
    text = "short"
    assert truncate_for_alert(text, max_chars=100) == text


def test_truncate_long_text() -> None:
    text = "x" * 600
    result = truncate_for_alert(text, max_chars=500)
    assert result.startswith("x" * 500)
    assert "100 more chars truncated" in result


def test_truncate_exact_boundary() -> None:
    text = "a" * 500
    assert truncate_for_alert(text, max_chars=500) == text
