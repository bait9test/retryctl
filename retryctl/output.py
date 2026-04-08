"""Capture and format command output for retryctl."""

from __future__ import annotations

import textwrap
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class OutputMode(str, Enum):
    SILENT = "silent"      # suppress all output
    PASSTHROUGH = "passthrough"  # stream directly to terminal
    CAPTURE = "capture"    # capture and replay on failure
    TAIL = "tail"          # only show last N lines on failure


@dataclass
class OutputConfig:
    mode: OutputMode = OutputMode.PASSTHROUGH
    tail_lines: int = 20
    show_on_success: bool = False
    show_on_failure: bool = True
    prefix: str = ""  # prepend each line with this string


@dataclass
class CapturedOutput:
    stdout_lines: List[str] = field(default_factory=list)
    stderr_lines: List[str] = field(default_factory=list)

    def append_stdout(self, line: str) -> None:
        self.stdout_lines.append(line)

    def append_stderr(self, line: str) -> None:
        self.stderr_lines.append(line)

    @property
    def stdout(self) -> str:
        return "\n".join(self.stdout_lines)

    @property
    def stderr(self) -> str:
        return "\n".join(self.stderr_lines)


def format_output(
    captured: CapturedOutput,
    config: OutputConfig,
    succeeded: bool,
) -> Optional[str]:
    """Return a formatted string to display, or None if output should be suppressed."""
    if config.mode == OutputMode.SILENT:
        return None
    if succeeded and not config.show_on_success:
        return None
    if not succeeded and not config.show_on_failure:
        return None

    lines: List[str] = []
    if captured.stdout_lines:
        lines.append("[stdout]")
        src = captured.stdout_lines
        if config.mode == OutputMode.TAIL:
            src = src[-config.tail_lines :]
        lines.extend(src)

    if captured.stderr_lines:
        lines.append("[stderr]")
        src = captured.stderr_lines
        if config.mode == OutputMode.TAIL:
            src = src[-config.tail_lines :]
        lines.extend(src)

    if not lines:
        return None

    if config.prefix:
        lines = [f"{config.prefix}{l}" for l in lines]

    return "\n".join(lines)


def truncate_for_alert(text: str, max_chars: int = 500) -> str:
    """Shorten long output before embedding in an alert message."""
    if len(text) <= max_chars:
        return text
    kept = text[:max_chars]
    omitted = len(text) - max_chars
    return f"{kept}\n... ({omitted} more chars truncated)"
