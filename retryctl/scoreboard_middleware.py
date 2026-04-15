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


def is_key_healthy(cfg: ScoreboardConfig, key: str, min_ratio: float = 0.5) -> bool:
    """Return True if the success ratio for *key* meets *min_ratio* (0.0–1.0).

    Returns True when the scoreboard is disabled or there is no data yet,
    so callers can treat an absent history as healthy by default.
    """
    if not cfg.enabled:
        return True
    tracker = ScoreboardTracker.load(cfg)
    summary = tracker.summary(key=key)
    entry = summary.get(key)
    if entry is None or entry["attempts"] == 0:
        return True
    return entry["ratio"] >= min_ratio
