"""probe.py – pre-flight health-check before each attempt.

A probe runs a shell command (or hits a URL) before the main command is
executed.  If the probe fails the attempt is skipped and the delay is
applied as normal.
"""
from __future__ import annotations

import subprocess
import logging
from dataclasses import dataclass, field
from typing import List, Optional

log = logging.getLogger(__name__)


@dataclass
class ProbeConfig:
    enabled: bool = False
    command: List[str] = field(default_factory=list)
    timeout: float = 5.0
    retries: int = 1
    skip_on_fail: bool = True  # skip attempt rather than abort run

    @staticmethod
    def from_dict(raw: dict) -> "ProbeConfig":
        if not isinstance(raw, dict):
            raise TypeError(f"probe config must be a dict, got {type(raw).__name__}")
        cmd = raw.get("command", [])
        if isinstance(cmd, str):
            import shlex
            cmd = shlex.split(cmd)
        if not isinstance(cmd, list):
            raise TypeError("probe.command must be a string or list")
        timeout = float(raw.get("timeout", 5.0))
        if timeout <= 0:
            raise ValueError("probe.timeout must be positive")
        retries = int(raw.get("retries", 1))
        if retries < 1:
            raise ValueError("probe.retries must be >= 1")
        enabled = bool(raw.get("enabled", bool(cmd)))
        return ProbeConfig(
            enabled=enabled,
            command=cmd,
            timeout=timeout,
            retries=retries,
            skip_on_fail=bool(raw.get("skip_on_fail", True)),
        )


class ProbeSkip(Exception):
    """Raised when the probe fails and skip_on_fail is True."""
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def run_probe(cfg: ProbeConfig) -> bool:
    """Run the probe command up to cfg.retries times.

    Returns True on success, False if all retries fail.
    """
    if not cfg.enabled or not cfg.command:
        return True
    for attempt in range(1, cfg.retries + 1):
        try:
            result = subprocess.run(
                cfg.command,
                timeout=cfg.timeout,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            if result.returncode == 0:
                log.debug("probe passed on attempt %d", attempt)
                return True
            log.warning(
                "probe failed (exit %d) on attempt %d/%d",
                result.returncode, attempt, cfg.retries,
            )
        except subprocess.TimeoutExpired:
            log.warning("probe timed out on attempt %d/%d", attempt, cfg.retries)
        except OSError as exc:
            log.warning("probe error on attempt %d/%d: %s", attempt, cfg.retries, exc)
    return False


def check_probe(cfg: ProbeConfig) -> None:
    """Run the probe and raise ProbeSkip if it fails and skip_on_fail is set."""
    if not cfg.enabled:
        return
    ok = run_probe(cfg)
    if not ok:
        if cfg.skip_on_fail:
            raise ProbeSkip("probe command did not succeed; skipping attempt")
        log.warning("probe failed but skip_on_fail=False; proceeding anyway")
