"""mirror_middleware.py — helpers for wiring MirrorConfig into the retry pipeline."""
from __future__ import annotations

import logging
from typing import Any, Dict

from retryctl.mirror import MirrorConfig, MirrorResult, mirror_output

log = logging.getLogger(__name__)


def parse_mirror(raw_config: Dict[str, Any]) -> MirrorConfig:
    """Extract and parse the [mirror] section from a raw config dict."""
    section = raw_config.get("mirror", {})
    if not isinstance(section, dict):
        raise TypeError(f"[mirror] section must be a dict, got {type(section).__name__}")
    return MirrorConfig.from_dict(section)


def mirror_config_to_dict(cfg: MirrorConfig) -> Dict[str, Any]:
    """Serialise a MirrorConfig back to a plain dict (for audit / state persistence)."""
    return {
        "enabled": cfg.enabled,
        "output_file": cfg.output_file,
        "pipe_cmd": cfg.pipe_cmd,
        "on_failure_only": cfg.on_failure_only,
    }


def on_attempt_complete(
    cfg: MirrorConfig,
    stdout: str,
    stderr: str,
    exit_code: int,
) -> MirrorResult:
    """Call after each attempt to mirror its output. Logs warnings on errors."""
    result = mirror_output(cfg, stdout, stderr, exit_code)
    if result.error:
        log.warning("mirror: sink error — %s", result.error)
    elif cfg.enabled:
        parts = []
        if result.lines_written:
            parts.append(f"{result.lines_written} lines → {cfg.output_file}")
        if result.pipe_returncode is not None:
            parts.append(f"pipe exited {result.pipe_returncode}")
        if parts:
            log.debug("mirror: %s", ", ".join(parts))
    return result


def describe_mirror(cfg: MirrorConfig) -> str:
    """Return a human-readable summary of the mirror configuration."""
    if not cfg.enabled:
        return "mirror: disabled"
    sinks = []
    if cfg.output_file:
        sinks.append(f"file={cfg.output_file}")
    if cfg.pipe_cmd:
        sinks.append(f"pipe={' '.join(cfg.pipe_cmd)}")
    qualifier = " (on failure only)" if cfg.on_failure_only else ""
    return f"mirror: enabled — {', '.join(sinks)}{qualifier}"
