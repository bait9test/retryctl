"""roster_middleware.py – helpers for wiring RosterConfig into the CLI pipeline."""
from __future__ import annotations

from typing import Any, Dict

from retryctl.roster import RosterConfig, list_entries, record_run


def parse_roster(config: Dict[str, Any]) -> RosterConfig:
    """Build a RosterConfig from the raw TOML config dict."""
    section = config.get("roster", {})
    if not isinstance(section, dict):
        raise TypeError("[roster] config section must be a mapping")
    return RosterConfig.from_dict(section)


def roster_config_to_dict(cfg: RosterConfig) -> Dict[str, Any]:
    """Serialise a RosterConfig back to a plain dict (useful for tests/debug)."""
    return {
        "enabled": cfg.enabled,
        "roster_file": cfg.roster_file,
        "max_entries": cfg.max_entries,
    }


def on_run_complete(
    cfg: RosterConfig,
    command: str,
    *,
    succeeded: bool,
) -> None:
    """Call after every run attempt to update the roster."""
    record_run(cfg, command, succeeded=succeeded)


def describe_roster(cfg: RosterConfig) -> str:
    """Return a human-readable summary of the top roster entries."""
    if not cfg.enabled:
        return "roster: disabled"
    entries = list_entries(cfg)
    if not entries:
        return "roster: no entries recorded yet"
    lines = ["roster (top entries):"]
    for e in entries[:10]:
        lines.append(
            f"  {e.command!r:50s}  runs={e.run_count}  failures={e.failure_count}"
        )
    return "\n".join(lines)
