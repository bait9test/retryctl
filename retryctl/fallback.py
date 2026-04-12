"""Fallback command support — run an alternative command when all retries are exhausted."""
from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass, field
from typing import List, Optional

log = logging.getLogger(__name__)


@dataclass
class FallbackConfig:
    enabled: bool = False
    command: List[str] = field(default_factory=list)
    timeout: Optional[float] = None
    capture_output: bool = True

    @staticmethod
    def from_dict(data: dict) -> "FallbackConfig":
        if not isinstance(data, dict):
            raise TypeError(f"FallbackConfig expects a dict, got {type(data).__name__}")
        raw_cmd = data.get("command", [])
        if isinstance(raw_cmd, str):
            raw_cmd = raw_cmd.split()
        if not isinstance(raw_cmd, list):
            raise TypeError("fallback.command must be a string or list")
        timeout = data.get("timeout")
        if timeout is not None:
            timeout = float(timeout)
            if timeout <= 0:
                raise ValueError("fallback.timeout must be positive")
        enabled = bool(data.get("enabled", bool(raw_cmd)))
        return FallbackConfig(
            enabled=enabled,
            command=[str(c) for c in raw_cmd],
            timeout=timeout,
            capture_output=bool(data.get("capture_output", True)),
        )


@dataclass
class FallbackResult:
    ran: bool
    exit_code: Optional[int] = None
    stdout: str = ""
    stderr: str = ""


def run_fallback(cfg: FallbackConfig) -> FallbackResult:
    """Execute the fallback command and return its result."""
    if not cfg.enabled or not cfg.command:
        return FallbackResult(ran=False)

    log.info("Running fallback command: %s", cfg.command)
    try:
        proc = subprocess.run(
            cfg.command,
            timeout=cfg.timeout,
            capture_output=cfg.capture_output,
            text=True,
        )
        if proc.returncode != 0:
            log.warning("Fallback command exited with code %d", proc.returncode)
        else:
            log.info("Fallback command succeeded")
        return FallbackResult(
            ran=True,
            exit_code=proc.returncode,
            stdout=proc.stdout or "",
            stderr=proc.stderr or "",
        )
    except subprocess.TimeoutExpired:
        log.error("Fallback command timed out after %s seconds", cfg.timeout)
        return FallbackResult(ran=True, exit_code=-1, stderr="timeout")
    except Exception as exc:  # noqa: BLE001
        log.error("Fallback command raised an exception: %s", exc)
        return FallbackResult(ran=True, exit_code=-1, stderr=str(exc))
