"""Pre/post execution hooks for retryctl.

Supports running shell commands or calling Python callables before the first
attempt and after the final attempt (success or failure).
"""

from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass, field
from typing import Callable, Optional

log = logging.getLogger(__name__)


@dataclass
class HookConfig:
    """Configuration for pre/post hooks."""

    pre_command: Optional[str] = None   # shell command to run before first attempt
    post_command: Optional[str] = None  # shell command to run after final attempt
    on_success: list[Callable[[], None]] = field(default_factory=list)
    on_failure: list[Callable[[], None]] = field(default_factory=list)


def run_hook_command(cmd: str, label: str) -> bool:
    """Run a shell hook command.  Returns True on success, False otherwise."""
    log.debug("Running %s hook: %s", label, cmd)
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            log.warning(
                "%s hook exited with code %d: %s",
                label,
                result.returncode,
                result.stderr.strip(),
            )
            return False
        return True
    except Exception as exc:  # pragma: no cover
        log.error("%s hook raised an exception: %s", label, exc)
        return False


def dispatch_hooks(callbacks: list[Callable[[], None]], label: str) -> None:
    """Invoke a list of Python callables, logging any errors."""
    for cb in callbacks:
        try:
            cb()
        except Exception as exc:
            log.error("%s hook callback %r raised: %s", label, cb, exc)


def run_pre_hooks(config: HookConfig) -> None:
    """Execute all configured pre-run hooks."""
    if config.pre_command:
        run_hook_command(config.pre_command, "pre")


def run_post_hooks(config: HookConfig, *, succeeded: bool) -> None:
    """Execute all configured post-run hooks based on outcome."""
    if config.post_command:
        run_hook_command(config.post_command, "post")

    if succeeded:
        dispatch_hooks(config.on_success, "on_success")
    else:
        dispatch_hooks(config.on_failure, "on_failure")
