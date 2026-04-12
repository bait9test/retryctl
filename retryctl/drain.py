"""drain.py — output drain with line-level callbacks for stdout/stderr streams."""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Callable, IO, List, Optional


@dataclass
class DrainConfig:
    enabled: bool = False
    max_lines: int = 0          # 0 = unlimited
    on_stdout: Optional[Callable[[str], None]] = None
    on_stderr: Optional[Callable[[str], None]] = None

    @classmethod
    def from_dict(cls, raw: dict) -> "DrainConfig":
        if not isinstance(raw, dict):
            raise TypeError(f"drain config must be a dict, got {type(raw).__name__}")
        max_lines = int(raw.get("max_lines", 0))
        if max_lines < 0:
            raise ValueError("drain.max_lines must be >= 0")
        enabled = bool(raw.get("enabled", False))
        return cls(enabled=enabled, max_lines=max_lines)


@dataclass
class DrainResult:
    stdout_lines: List[str] = field(default_factory=list)
    stderr_lines: List[str] = field(default_factory=list)

    @property
    def stdout(self) -> str:
        return "\n".join(self.stdout_lines)

    @property
    def stderr(self) -> str:
        return "\n".join(self.stderr_lines)


def _drain_stream(
    stream: IO[bytes],
    lines: List[str],
    max_lines: int,
    callback: Optional[Callable[[str], None]],
) -> None:
    """Read *stream* line-by-line, storing and optionally forwarding each line."""
    for raw in stream:
        line = raw.decode(errors="replace").rstrip("\n")
        if max_lines == 0 or len(lines) < max_lines:
            lines.append(line)
        if callback is not None:
            try:
                callback(line)
            except Exception:  # noqa: BLE001
                pass


def drain_process(
    proc,  # subprocess.Popen instance
    cfg: DrainConfig,
) -> DrainResult:
    """Drain stdout and stderr from *proc* concurrently.

    Returns a :class:`DrainResult` once the process streams are exhausted.
    The caller is responsible for calling ``proc.wait()`` afterwards.
    """
    result = DrainResult()
    if not cfg.enabled:
        return result

    t_out = threading.Thread(
        target=_drain_stream,
        args=(proc.stdout, result.stdout_lines, cfg.max_lines, cfg.on_stdout),
        daemon=True,
    )
    t_err = threading.Thread(
        target=_drain_stream,
        args=(proc.stderr, result.stderr_lines, cfg.max_lines, cfg.on_stderr),
        daemon=True,
    )
    t_out.start()
    t_err.start()
    t_out.join()
    t_err.join()
    return result
