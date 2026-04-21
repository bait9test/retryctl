"""gating.py — conditional gate that blocks retries based on an external command exit code."""
from __future__ import annotations

import logging
import shlex
import subprocess
from dataclasses import dataclass, field
from typing import List, Optional

log = logging.getLogger(__name__)


@dataclass
class GatingConfig:
    enabled: bool = False
    command: List[str] = field(default_factory=list)
    timeout: float = 10.0
    allow_on_error: bool = True  # if gate command itself fails, allow through

    @staticmethod
    def from_dict(data: dict) -> "GatingConfig":
        if not isinstance(data, dict):
            raise TypeError(f"gating config must be a dict, got {type(data).__name__}")
        raw_cmd = data.get("command", [])
        if isinstance(raw_cmd, str):
            raw_cmd = shlex.split(raw_cmd)
        if not isinstance(raw_cmd, list):
            raise TypeError("gating.command must be a string or list")
        timeout = float(data.get("timeout", 10.0))
        if timeout <= 0:
            raise ValueError("gating.timeout must be positive")
        enabled = bool(data.get("enabled", bool(raw_cmd)))
        return GatingConfig(
            enabled=enabled,
            command=raw_cmd,
            timeout=timeout,
            allow_on_error=bool(data.get("allow_on_error", True)),
        )


class GateBlocked(Exception):
    def __init__(self, command: List[str], exit_code: int) -> None:
        self.command = command
        self.exit_code = exit_code
        super().__init__(f"gate blocked: {' '.join(command)!r} exited {exit_code}")


def check_gate(cfg: GatingConfig) -> None:
    """Run the gate command. Raises GateBlocked if it exits non-zero.

    Args:
        cfg: The gating configuration to use.

    Raises:
        GateBlocked: If the gate command exits with a non-zero code, or if the
            command itself fails and ``allow_on_error`` is ``False``.
    """
    if not cfg.enabled or not cfg.command:
        return
    try:
        result = subprocess.run(
            cfg.command,
            timeout=cfg.timeout,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except subprocess.TimeoutExpired as exc:
        log.warning(
            "gating: gate command timed out after %.1fs (allowing through: %s)",
            cfg.timeout,
            cfg.allow_on_error,
        )
        if cfg.allow_on_error:
            return
        raise GateBlocked(cfg.command, -1) from exc
    except Exception as exc:  # noqa: BLE001
        if cfg.allow_on_error:
            log.warning("gating: gate command error (allowing through): %s", exc)
            return
        raise GateBlocked(cfg.command, -1) from exc

    if result.returncode != 0:
        log.debug(
            "gating: gate command exited %d — blocking attempt", result.returncode
        )
        raise GateBlocked(cfg.command, result.returncode)
    log.debug("gating: gate command passed (exit 0)")
