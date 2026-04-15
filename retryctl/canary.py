"""Canary check — run a lightweight probe before committing to a full retry.

If the canary command fails, the attempt is skipped and counted as a
canary-blocked skip rather than a real failure.
"""
from __future__ import annotations

import logging
import shlex
import subprocess
from dataclasses import dataclass, field
from typing import List, Optional

log = logging.getLogger(__name__)


@dataclass
class CanaryConfig:
    enabled: bool = False
    command: List[str] = field(default_factory=list)
    timeout: float = 5.0
    skip_on_failure: bool = True  # if False, treat canary failure as fatal

    @staticmethod
    def from_dict(raw: dict) -> "CanaryConfig":
        if not isinstance(raw, dict):
            raise TypeError(f"canary config must be a dict, got {type(raw).__name__}")
        cmd = raw.get("command", [])
        if isinstance(cmd, str):
            cmd = shlex.split(cmd)
        if not isinstance(cmd, list):
            raise TypeError("canary.command must be a string or list")
        timeout = float(raw.get("timeout", 5.0))
        if timeout <= 0:
            raise ValueError("canary.timeout must be positive")
        enabled = bool(raw.get("enabled", bool(cmd)))
        return CanaryConfig(
            enabled=enabled,
            command=cmd,
            timeout=timeout,
            skip_on_failure=bool(raw.get("skip_on_failure", True)),
        )


class CanaryBlocked(Exception):
    """Raised when the canary check fails and skip_on_failure is False."""

    def __init__(self, returncode: int) -> None:
        self.returncode = returncode
        super().__init__(f"canary check failed with exit code {returncode}")


def run_canary(cfg: CanaryConfig) -> bool:
    """Run the canary command.  Returns True if healthy, False otherwise.

    Raises CanaryBlocked when skip_on_failure is False and the check fails.
    """
    if not cfg.enabled or not cfg.command:
        return True
    try:
        result = subprocess.run(
            cfg.command,
            timeout=cfg.timeout,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if result.returncode == 0:
            log.debug("canary check passed")
            return True
        log.warning("canary check failed (exit %d)", result.returncode)
        if not cfg.skip_on_failure:
            raise CanaryBlocked(result.returncode)
        return False
    except subprocess.TimeoutExpired:
        log.warning("canary check timed out after %.1fs", cfg.timeout)
        if not cfg.skip_on_failure:
            raise CanaryBlocked(-1)
        return False
