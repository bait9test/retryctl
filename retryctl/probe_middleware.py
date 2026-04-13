"""probe_middleware.py – helpers for wiring ProbeConfig into the CLI/config layer."""
from __future__ import annotations

from typing import Any, Dict

from retryctl.probe import ProbeConfig, check_probe


def parse_probe(raw_config: Dict[str, Any]) -> ProbeConfig:
    """Extract and parse the [probe] section from a raw config dict."""
    section = raw_config.get("probe", {})
    if not isinstance(section, dict):
        raise TypeError(f"[probe] must be a table, got {type(section).__name__}")
    return ProbeConfig.from_dict(section)


def probe_config_to_dict(cfg: ProbeConfig) -> Dict[str, Any]:
    """Serialise a ProbeConfig back to a plain dict (for audit / debug output)."""
    return {
        "enabled": cfg.enabled,
        "command": cfg.command,
        "timeout": cfg.timeout,
        "retries": cfg.retries,
        "skip_on_fail": cfg.skip_on_fail,
    }


def before_attempt(cfg: ProbeConfig) -> None:
    """Call this hook before each retry attempt to enforce the probe gate."""
    check_probe(cfg)


def describe_probe(cfg: ProbeConfig) -> str:
    """Return a human-readable summary of the probe configuration."""
    if not cfg.enabled:
        return "probe: disabled"
    cmd_str = " ".join(cfg.command) if cfg.command else "<none>"
    return (
        f"probe: enabled | command={cmd_str!r} "
        f"timeout={cfg.timeout}s retries={cfg.retries} "
        f"skip_on_fail={cfg.skip_on_fail}"
    )
