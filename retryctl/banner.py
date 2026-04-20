"""Banner — display a startup/summary banner for retryctl runs."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

log = logging.getLogger(__name__)


@dataclass
class BannerConfig:
    enabled: bool = False
    show_command: bool = True
    show_config: bool = False
    show_version: bool = True
    prefix: str = "[retryctl]"

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "BannerConfig":
        if not isinstance(raw, dict):
            raise TypeError(f"BannerConfig expects a dict, got {type(raw).__name__}")
        enabled = bool(raw.get("enabled", False))
        show_command = bool(raw.get("show_command", True))
        show_config = bool(raw.get("show_config", False))
        show_version = bool(raw.get("show_version", True))
        prefix = str(raw.get("prefix", "[retryctl]"))
        return cls(
            enabled=enabled,
            show_command=show_command,
            show_config=show_config,
            show_version=show_version,
            prefix=prefix,
        )


def build_banner_lines(
    cfg: BannerConfig,
    *,
    command: list[str] | None = None,
    config_path: str | None = None,
    version: str = "unknown",
) -> list[str]:
    """Return the list of banner lines to display (empty if disabled)."""
    if not cfg.enabled:
        return []

    lines: list[str] = []
    p = cfg.prefix

    if cfg.show_version:
        lines.append(f"{p} retryctl v{version}")
    if cfg.show_command and command:
        lines.append(f"{p} command : {' '.join(command)}")
    if cfg.show_config and config_path:
        lines.append(f"{p} config  : {config_path}")

    return lines


def emit_banner(
    cfg: BannerConfig,
    *,
    command: list[str] | None = None,
    config_path: str | None = None,
    version: str = "unknown",
) -> None:
    """Log each banner line at INFO level."""
    for line in build_banner_lines(
        cfg, command=command, config_path=config_path, version=version
    ):
        log.info(line)
