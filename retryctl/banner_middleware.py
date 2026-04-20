"""Banner middleware — parse config and wire banner emission into the run lifecycle."""
from __future__ import annotations

from typing import Any

from retryctl.banner import BannerConfig, emit_banner


def parse_banner(raw_config: dict[str, Any]) -> BannerConfig:
    """Extract [banner] section from the top-level config dict."""
    section = raw_config.get("banner", {})
    if not isinstance(section, dict):
        raise TypeError(
            f"[banner] must be a table, got {type(section).__name__}"
        )
    return BannerConfig.from_dict(section)


def banner_config_to_dict(cfg: BannerConfig) -> dict[str, Any]:
    """Serialise a BannerConfig back to a plain dict (for state / audit)."""
    return {
        "enabled": cfg.enabled,
        "show_command": cfg.show_command,
        "show_config": cfg.show_config,
        "show_version": cfg.show_version,
        "prefix": cfg.prefix,
    }


def before_run(
    cfg: BannerConfig,
    *,
    command: list[str] | None = None,
    config_path: str | None = None,
    version: str = "unknown",
) -> None:
    """Call this before the first attempt to emit the startup banner."""
    emit_banner(cfg, command=command, config_path=config_path, version=version)


def describe_banner(cfg: BannerConfig) -> str:
    """Human-readable summary of the banner configuration."""
    if not cfg.enabled:
        return "banner: disabled"
    parts = []
    if cfg.show_version:
        parts.append("version")
    if cfg.show_command:
        parts.append("command")
    if cfg.show_config:
        parts.append("config")
    shown = ", ".join(parts) if parts else "nothing"
    return f"banner: enabled (shows {shown})"
