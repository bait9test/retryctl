"""Middleware helpers for integrating replay into the retry pipeline."""
from __future__ import annotations

import logging
from typing import List, Optional

from retryctl.replay import ReplayConfig, ReplayRecord, save_replay, load_replay, clear_replay

log = logging.getLogger(__name__)


def parse_replay(raw: dict) -> ReplayConfig:
    """Extract [replay] section from raw config dict."""
    section = raw.get("replay", {})
    if not isinstance(section, dict):
        raise TypeError("[replay] must be a TOML table")
    return ReplayConfig.from_dict(section)


def replay_config_to_dict(cfg: ReplayConfig) -> dict:
    return {"enabled": cfg.enabled, "replay_dir": cfg.replay_dir}


def on_run_failed(
    cfg: ReplayConfig,
    command: List[str],
    exit_code: int,
    attempt_count: int,
    label: Optional[str] = None,
) -> None:
    """Persist a replay record after a failed run."""
    if not cfg.enabled:
        return
    record = ReplayRecord(
        command=command,
        exit_code=exit_code,
        attempt_count=attempt_count,
        label=label,
    )
    save_replay(cfg, record)
    log.debug("replay: saved record for label=%r exit_code=%d", label, exit_code)


def on_run_success(cfg: ReplayConfig, label: Optional[str] = None) -> None:
    """Clear any existing replay record on success."""
    if not cfg.enabled:
        return
    clear_replay(cfg, label)
    log.debug("replay: cleared record for label=%r", label)


def get_replay_command(
    cfg: ReplayConfig, label: Optional[str] = None
) -> Optional[List[str]]:
    """Return the command from the last recorded failure, if any."""
    record = load_replay(cfg, label)
    if record is None:
        return None
    log.info(
        "replay: found previous failure (exit=%d, attempts=%d) for label=%r",
        record.exit_code,
        record.attempt_count,
        label,
    )
    return record.command
