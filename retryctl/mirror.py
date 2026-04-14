"""mirror.py — duplicate command output to a secondary sink (file or command)."""
from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class MirrorConfig:
    enabled: bool = False
    # Write raw stdout/stderr lines to this file (appended)
    output_file: Optional[str] = None
    # Pipe combined output through this shell command
    pipe_cmd: Optional[List[str]] = None
    # Mirror only on failure (exit != 0)
    on_failure_only: bool = False

    @staticmethod
    def from_dict(raw: object) -> "MirrorConfig":
        if not isinstance(raw, dict):
            raise TypeError(f"mirror config must be a dict, got {type(raw).__name__}")
        enabled = bool(raw.get("enabled", False))
        output_file: Optional[str] = raw.get("output_file") or None
        pipe_cmd_raw = raw.get("pipe_cmd")
        if isinstance(pipe_cmd_raw, str):
            import shlex
            pipe_cmd: Optional[List[str]] = shlex.split(pipe_cmd_raw)
        elif isinstance(pipe_cmd_raw, list):
            pipe_cmd = [str(s) for s in pipe_cmd_raw]
        elif pipe_cmd_raw is None:
            pipe_cmd = None
        else:
            raise TypeError("mirror.pipe_cmd must be a string or list")
        on_failure_only = bool(raw.get("on_failure_only", False))
        # auto-enable when any sink is configured
        if (output_file or pipe_cmd) and not raw.get("enabled", False) is False:
            enabled = True
        if output_file or pipe_cmd:
            enabled = raw.get("enabled", True) is not False
        return MirrorConfig(
            enabled=enabled,
            output_file=output_file,
            pipe_cmd=pipe_cmd,
            on_failure_only=on_failure_only,
        )


@dataclass
class MirrorResult:
    lines_written: int = 0
    pipe_returncode: Optional[int] = None
    error: Optional[str] = None


def mirror_output(
    cfg: MirrorConfig,
    stdout: str,
    stderr: str,
    exit_code: int,
) -> MirrorResult:
    """Write/pipe combined output according to *cfg*. Returns a MirrorResult."""
    if not cfg.enabled:
        return MirrorResult()
    if cfg.on_failure_only and exit_code == 0:
        return MirrorResult()

    combined = ""
    if stdout:
        combined += stdout if stdout.endswith("\n") else stdout + "\n"
    if stderr:
        combined += stderr if stderr.endswith("\n") else stderr + "\n"

    lines_written = 0
    pipe_rc: Optional[int] = None
    err_msg: Optional[str] = None

    if cfg.output_file:
        try:
            with open(cfg.output_file, "a", encoding="utf-8") as fh:
                fh.write(combined)
                lines_written = combined.count("\n")
        except OSError as exc:
            err_msg = str(exc)

    if cfg.pipe_cmd:
        try:
            proc = subprocess.run(
                cfg.pipe_cmd,
                input=combined,
                capture_output=True,
                text=True,
                timeout=30,
            )
            pipe_rc = proc.returncode
        except Exception as exc:  # noqa: BLE001
            err_msg = str(exc)

    return MirrorResult(lines_written=lines_written, pipe_returncode=pipe_rc, error=err_msg)
