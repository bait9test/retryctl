"""Middleware that wires EnvConfig into the run_with_retry loop."""
from __future__ import annotations

import subprocess
from typing import List, Optional

from retryctl.env import EnvConfig, build_env


def build_subprocess_kwargs(
    cfg: EnvConfig,
    attempt: int,
    max_attempts: int,
    extra_kwargs: Optional[dict] = None,
) -> dict:
    """Return keyword arguments suitable for ``subprocess.run`` / ``Popen``.

    Merges the resolved environment into *extra_kwargs* (which may already
    contain ``cwd``, ``timeout``, etc.).
    """
    env = build_env(cfg, attempt=attempt, max_attempts=max_attempts)
    kwargs: dict = dict(extra_kwargs or {})
    kwargs["env"] = env
    return kwargs


def run_command_with_env(
    cmd: List[str],
    cfg: EnvConfig,
    attempt: int,
    max_attempts: int,
    **subprocess_kwargs,
) -> subprocess.CompletedProcess:
    """Run *cmd* with the environment resolved from *cfg*.

    Any additional keyword arguments are forwarded to ``subprocess.run``.
    """
    kwargs = build_subprocess_kwargs(
        cfg,
        attempt=attempt,
        max_attempts=max_attempts,
        extra_kwargs=subprocess_kwargs,
    )
    return subprocess.run(cmd, **kwargs)  # noqa: S603
