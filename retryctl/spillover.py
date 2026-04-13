"""spillover.py — shed excess retries to an overflow command when attempt count exceeds a threshold."""
from __future__ import annotations

import logging
import shlex
import subprocess
from dataclasses import dataclass, field
from typing import List, Optional

log = logging.getLogger(__name__)


@dataclass
class SpilloverConfig:
    enabled: bool = False
    threshold: int = 3          # attempt number at which spillover kicks in
    command: List[str] = field(default_factory=list)
    capture_output: bool = True
    timeout: Optional[float] = None

    @staticmethod
    def from_dict(raw: dict) -> "SpilloverConfig":
        if not isinstance(raw, dict):
            raise TypeError(f"spillover config must be a dict, got {type(raw).__name__}")

        cmd = raw.get("command", [])
        if isinstance(cmd, str):
            cmd = shlex.split(cmd)
        if not isinstance(cmd, list):
            raise TypeError("spillover.command must be a string or list")

        threshold = int(raw.get("threshold", 3))
        if threshold < 1:
            raise ValueError("spillover.threshold must be >= 1")

        enabled = bool(raw.get("enabled", bool(cmd)))

        timeout = raw.get("timeout")
        if timeout is not None:
            timeout = float(timeout)
            if timeout <= 0:
                raise ValueError("spillover.timeout must be positive")

        return SpilloverConfig(
            enabled=enabled,
            threshold=threshold,
            command=cmd,
            capture_output=bool(raw.get("capture_output", True)),
            timeout=timeout,
        )


@dataclass
class SpilloverResult:
    triggered: bool
    returncode: Optional[int] = None
    stdout: str = ""
    stderr: str = ""


def run_spillover(cfg: SpilloverConfig, attempt: int, original_command: List[str]) -> SpilloverResult:
    """Run the overflow command if attempt >= threshold. Passes original command as env var."""
    if not cfg.enabled or attempt < cfg.threshold:
        return SpilloverResult(triggered=False)

    if not cfg.command:
        log.warning("spillover triggered but no command configured")
        return SpilloverResult(triggered=True)

    log.info("spillover triggered on attempt %d (threshold=%d)", attempt, cfg.threshold)
    try:
        result = subprocess.run(
            cfg.command,
            capture_output=cfg.capture_output,
            timeout=cfg.timeout,
            text=True,
        )
        return SpilloverResult(
            triggered=True,
            returncode=result.returncode,
            stdout=result.stdout or "",
            stderr=result.stderr or "",
        )
    except subprocess.TimeoutExpired:
        log.error("spillover command timed out after %ss", cfg.timeout)
        return SpilloverResult(triggered=True, returncode=-1, stderr="timeout")
    except Exception as exc:  # noqa: BLE001
        log.error("spillover command failed: %s", exc)
        return SpilloverResult(triggered=True, returncode=-1, stderr=str(exc))
