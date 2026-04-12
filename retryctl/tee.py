"""tee.py — capture and simultaneously stream command output."""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from typing import IO, List, Optional


@dataclass
class TeeConfig:
    enabled: bool = False
    stdout_file: Optional[str] = None
    stderr_file: Optional[str] = None
    append: bool = False

    @classmethod
    def from_dict(cls, raw: object) -> "TeeConfig":
        if not isinstance(raw, dict):
            raise TypeError(f"tee config must be a dict, got {type(raw).__name__}")
        enabled = bool(raw.get("enabled", False))
        stdout_file = raw.get("stdout_file") or None
        stderr_file = raw.get("stderr_file") or None
        append = bool(raw.get("append", False))
        if stdout_file or stderr_file:
            enabled = True
        return cls(
            enabled=enabled,
            stdout_file=stdout_file,
            stderr_file=stderr_file,
            append=append,
        )


@dataclass
class TeeResult:
    stdout_lines: List[str] = field(default_factory=list)
    stderr_lines: List[str] = field(default_factory=list)

    @property
    def stdout(self) -> str:
        return "".join(self.stdout_lines)

    @property
    def stderr(self) -> str:
        return "".join(self.stderr_lines)


def _open_file(path: str, append: bool) -> IO[str]:
    mode = "a" if append else "w"
    return open(path, mode, encoding="utf-8")


def tee_lines(
    lines: List[str],
    stream: IO[str],
    file_path: Optional[str],
    append: bool,
) -> None:
    """Write *lines* to *stream* and optionally to a file."""
    for line in lines:
        stream.write(line)
    stream.flush()
    if file_path:
        with _open_file(file_path, append) as fh:
            fh.writelines(lines)


def apply_tee(cfg: TeeConfig, result: TeeResult) -> None:
    """Tee captured stdout/stderr according to *cfg*."""
    if not cfg.enabled:
        return
    tee_lines(result.stdout_lines, sys.stdout, cfg.stdout_file, cfg.append)
    tee_lines(result.stderr_lines, sys.stderr, cfg.stderr_file, cfg.append)
