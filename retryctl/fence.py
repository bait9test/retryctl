"""fence.py — execution fence: block retries until a prerequisite command succeeds."""
from __future__ import annotations

import logging
import shlex
import subprocess
from dataclasses import dataclass, field
from typing import List, Optional

log = logging.getLogger(__name__)


@dataclass
class FenceConfig:
    enabled: bool = False
    command: List[str] = field(default_factory=list)
    timeout: float = 10.0
    on_fail: str = "block"  # "block" | "warn" | "skip"

    @staticmethod
    def from_dict(raw: dict) -> "FenceConfig":
        if not isinstance(raw, dict):
            raise TypeError(f"fence config must be a dict, got {type(raw).__name__}")

        cmd = raw.get("command", [])
        if isinstance(cmd, str):
            cmd = shlex.split(cmd)
        if not isinstance(cmd, list):
            raise TypeError("fence.command must be a string or list")

        timeout = float(raw.get("timeout", 10.0))
        if timeout <= 0:
            raise ValueError("fence.timeout must be positive")

        on_fail = str(raw.get("on_fail", "block"))
        if on_fail not in ("block", "warn", "skip"):
            raise ValueError(f"fence.on_fail must be 'block', 'warn', or 'skip'; got {on_fail!r}")

        enabled = bool(raw.get("enabled", bool(cmd)))
        return FenceConfig(enabled=enabled, command=cmd, timeout=timeout, on_fail=on_fail)


class FenceBlocked(Exception):
    def __init__(self, command: List[str], returncode: int) -> None:
        self.command = command
        self.returncode = returncode
        super().__init__(
            f"Fence command {command!r} failed with exit code {returncode}; blocking retry."
        )


def check_fence(cfg: FenceConfig) -> bool:
    """Run the fence command.  Return True if the fence passes (command exits 0).

    Raises FenceBlocked when on_fail='block' and the command fails.
    Returns False (with a warning) when on_fail='warn'.
    Returns True unconditionally when on_fail='skip'.
    """
    if not cfg.enabled or not cfg.command:
        return True

    log.debug("Running fence command: %s", cfg.command)
    try:
        result = subprocess.run(
            cfg.command,
            timeout=cfg.timeout,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except subprocess.TimeoutExpired:
        log.warning("Fence command timed out after %.1fs: %s", cfg.timeout, cfg.command)
        returncode = -1
    except OSError as exc:
        log.warning("Fence command could not be run: %s", exc)
        returncode = -1
    else:
        returncode = result.returncode
        if result.stderr:
            log.debug("Fence stderr: %s", result.stderr.decode(errors="replace").strip())

    if returncode == 0:
        log.debug("Fence passed.")
        return True

    if cfg.on_fail == "block":
        raise FenceBlocked(cfg.command, returncode)
    if cfg.on_fail == "warn":
        log.warning("Fence command failed (exit %d); continuing anyway.", returncode)
        return False
    # on_fail == "skip"
    log.debug("Fence command failed; skipping fence check as configured.")
    return True
