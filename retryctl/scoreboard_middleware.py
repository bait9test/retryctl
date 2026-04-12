"""scoreboard_middleware.py – wires ScoreboardTracker into the retryctl pipeline."""
from __future__ import annotations

from typing import Optional

from retryctl.scoreboard import ScoreboardConfig, ScoreboardTracker


def parse_scoreboard(raw_config: dict) -> ScoreboardConfig:
    """Extract [scoreboard] section from the top-level config dict."""
    section = raw_config.get("scoreboard", {})
    if not isinstance(section, dict):
        raise TypeError(f"[scoreboard] must be a table, got {type(section).__name__}")
    return ScoreboardConfig.from_dict(section)


def scoreboard_config_to_dict(cfg: ScoreboardConfig) -> dict:
    return {
        "enabled": cfg.enabled,
        "file": cfg.file,
        "window_seconds": cfg.window_seconds,
    }


def record_run_outcome(
    tracker: ScoreboardTracker,
    key: str,
    succeeded: bool,
) -> None:
    """Call after a run completes to register the outcome."""
    tracker.record(key=key, succeeded=succeeded)


def describe_scoreboard(cfg: ScoreboardConfig, key: Optional[str] = None) -> str:
    if not cfg.enabled:
        return "scoreboard disabled"
    tracker = ScoreboardTracker.load(cfg)
    summary = tracker.summary(key=key)
    if not summary:
        return "scoreboard: no data in window"
    lines = ["scoreboard summary:"]
    for k, v in sorted(summary.items()):
        lines.append(
            f"  {k}: {v['attempts']} attempts, "
            f"{v['successes']} ok, {v['failures']} failed "
            f"(ratio={v['ratio']})"
        )
    return "\n".join(lines)
