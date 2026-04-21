"""ripple.py — propagate failure signals to downstream commands.

When a run fails, Ripple fires a configurable shell command so that
dependent systems can react immediately rather than waiting for the
next scheduled check.
"""
from __future__ import annotations

import logging
import shlex
import subprocess
from dataclasses import dataclass, field
from typing import List, Optional

log = logging.getLogger(__name__)


@dataclass
class RippleConfig:
    enabled: bool = False
    command: List[str] = field(default_factory=list)
    on_failure: bool = True
    on_success: bool = False
    timeout: float = 10.0

    @staticmethod
    def from_dict(raw: object) -> "RippleConfig":
        if not isinstance(raw, dict):
            raise TypeError(f"[ripple] config must be a table, got {type(raw).__name__}")

        cmd = raw.get("command", [])
        if isinstance(cmd, str):
            cmd = shlex.split(cmd)
        if not isinstance(cmd, list):
            raise TypeError("[ripple] 'command' must be a string or list")

        enabled = bool(raw.get("enabled", bool(cmd)))
        on_failure = bool(raw.get("on_failure", True))
        on_success = bool(raw.get("on_success", False))
        timeout = float(raw.get("timeout", 10.0))

        return RippleConfig(
            enabled=enabled,
            command=cmd,
            on_failure=on_failure,
            on_success=on_success,
            timeout=timeout,
        )


class RippleBlocked(Exception):
    """Raised internally if the ripple command itself fails (non-fatal)."""


def fire_ripple(cfg: RippleConfig, *, succeeded: bool) -> None:
    """Execute the ripple command if the outcome matches the config."""
    if not cfg.enabled or not cfg.command:
        return
    if succeeded and not cfg.on_success:
        return
    if not succeeded and not cfg.on_failure:
        return

    outcome = "success" if succeeded else "failure"
    log.debug("[ripple] firing ripple command for outcome=%s", outcome)
    try:
        result = subprocess.run(
            cfg.command,
            timeout=cfg.timeout,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            log.warning(
                "[ripple] command exited %d: %s",
                result.returncode,
                result.stderr.strip(),
            )
        else:
            log.debug("[ripple] command completed successfully")
    except subprocess.TimeoutExpired:
        log.warning("[ripple] command timed out after %.1fs", cfg.timeout)
    except Exception as exc:  # pragma: no cover
        log.warning("[ripple] command raised unexpected error: %s", exc)
