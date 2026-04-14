"""Shadow mode: run a secondary command alongside the primary, compare outcomes."""
from __future__ import annotations

import logging
import shlex
import subprocess
from dataclasses import dataclass, field
from typing import List, Optional

log = logging.getLogger(__name__)


@dataclass
class ShadowConfig:
    enabled: bool = False
    command: List[str] = field(default_factory=list)
    timeout: float = 10.0
    log_divergence: bool = True

    @staticmethod
    def from_dict(raw: dict) -> "ShadowConfig":
        if not isinstance(raw, dict):
            raise TypeError(f"shadow config must be a dict, got {type(raw).__name__}")
        cmd = raw.get("command", [])
        if isinstance(cmd, str):
            cmd = shlex.split(cmd)
        if not isinstance(cmd, list):
            raise TypeError("shadow.command must be a string or list")
        timeout = float(raw.get("timeout", 10.0))
        if timeout <= 0:
            raise ValueError("shadow.timeout must be positive")
        enabled = bool(raw.get("enabled", bool(cmd)))
        return ShadowConfig(
            enabled=enabled,
            command=cmd,
            timeout=timeout,
            log_divergence=bool(raw.get("log_divergence", True)),
        )


@dataclass
class ShadowResult:
    exit_code: Optional[int]
    stdout: str
    stderr: str
    timed_out: bool = False
    error: Optional[str] = None


def run_shadow(cfg: ShadowConfig) -> Optional[ShadowResult]:
    """Run the shadow command and return its result, or None if disabled."""
    if not cfg.enabled or not cfg.command:
        return None
    try:
        proc = subprocess.run(
            cfg.command,
            capture_output=True,
            text=True,
            timeout=cfg.timeout,
        )
        return ShadowResult(
            exit_code=proc.returncode,
            stdout=proc.stdout,
            stderr=proc.stderr,
        )
    except subprocess.TimeoutExpired:
        log.warning("shadow command timed out after %.1fs", cfg.timeout)
        return ShadowResult(exit_code=None, stdout="", stderr="", timed_out=True)
    except Exception as exc:  # noqa: BLE001
        log.warning("shadow command error: %s", exc)
        return ShadowResult(exit_code=None, stdout="", stderr="", error=str(exc))


def compare_shadow(primary_code: int, shadow: ShadowResult, cfg: ShadowConfig) -> bool:
    """Return True if primary and shadow outcomes agree (both zero or both non-zero)."""
    if shadow.timed_out or shadow.error or shadow.exit_code is None:
        return False
    primary_ok = primary_code == 0
    shadow_ok = shadow.exit_code == 0
    diverged = primary_ok != shadow_ok
    if diverged and cfg.log_divergence:
        log.warning(
            "shadow divergence: primary=%d shadow=%d",
            primary_code,
            shadow.exit_code,
        )
    return not diverged
