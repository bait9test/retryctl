"""Middleware helpers for integrating SuppressConfig into the retry loop."""
from __future__ import annotations

import logging
from typing import Optional

from retryctl.suppress import SuppressConfig, from_dict, is_suppressed

log = logging.getLogger(__name__)


def parse_suppress(config: dict) -> SuppressConfig:
    """Extract and parse the [suppress] section from a raw config dict."""
    section = config.get("suppress", {})
    if not isinstance(section, dict):
        raise TypeError(
            f"[suppress] must be a table, got {type(section).__name__}"
        )
    return from_dict(section)


def check_suppress_gate(
    cfg: SuppressConfig,
    exit_code: int,
    stdout: Optional[str] = None,
    stderr: Optional[str] = None,
) -> bool:
    """
    Return True (and log a debug message) when the result is suppressed.
    Callers should skip further failure handling when True is returned.
    """
    if is_suppressed(cfg, exit_code, stdout, stderr):
        log.debug(
            "exit_code=%d suppressed — treating attempt as non-failure",
            exit_code,
        )
        return True
    return False


def suppress_config_summary(cfg: SuppressConfig) -> str:
    """Return a human-readable one-liner describing active suppress rules."""
    if not cfg.enabled:
        return "suppress: disabled"
    parts = []
    if cfg.exit_codes:
        parts.append(f"exit_codes={cfg.exit_codes}")
    if cfg.stdout_patterns:
        parts.append(f"stdout_patterns={cfg.stdout_patterns}")
    if cfg.stderr_patterns:
        parts.append(f"stderr_patterns={cfg.stderr_patterns}")
    return "suppress: " + ", ".join(parts) if parts else "suppress: enabled (no rules)"
