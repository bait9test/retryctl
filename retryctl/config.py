"""Configuration loading for retryctl — supports TOML and env-var overrides."""

import os
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from retryctl.backoff import BackoffConfig, BackoffStrategy
from retryctl.alerts import AlertChannel, AlertConfig

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATHS = [
    Path("retryctl.toml"),
    Path(".retryctl.toml"),
    Path.home() / ".config" / "retryctl" / "config.toml",
]


@dataclass
class RetryCtlConfig:
    max_attempts: int = 3
    backoff: BackoffConfig = field(default_factory=BackoffConfig)
    alerts: AlertConfig = field(default_factory=AlertConfig)
    shell: str = "/bin/sh"
    capture_output: bool = True


def _load_toml(path: Path) -> dict:
    try:
        import tomllib  # Python 3.11+
    except ImportError:
        try:
            import tomli as tomllib  # type: ignore[no-redef]
        except ImportError:
            logger.debug("No TOML library available, skipping config file")
            return {}
    with path.open("rb") as f:
        return tomllib.load(f)


def _parse_backoff(raw: dict) -> BackoffConfig:
    strategy_str = raw.get("strategy", "fixed").upper()
    strategy = BackoffStrategy[strategy_str]
    return BackoffConfig(
        strategy=strategy,
        base_delay=float(raw.get("base_delay", 1.0)),
        max_delay=float(raw.get("max_delay", 60.0)),
        multiplier=float(raw.get("multiplier", 2.0)),
        jitter=bool(raw.get("jitter", False)),
    )


def _parse_alerts(raw: dict) -> AlertConfig:
    channels = [
        AlertChannel(c) for c in raw.get("channels", ["log"])
    ]
    return AlertConfig(
        channels=channels,
        email_to=raw.get("email_to"),
        email_from=raw.get("email_from"),
        smtp_host=raw.get("smtp_host", "localhost"),
        smtp_port=int(raw.get("smtp_port", 25)),
        webhook_url=raw.get("webhook_url"),
        min_attempts_before_alert=int(raw.get("min_attempts_before_alert", 1)),
    )


def load_config(path: Optional[Path] = None) -> RetryCtlConfig:
    """Load config from file (auto-discovered or explicit) with env-var overrides."""
    raw: dict = {}
    config_path = path
    if config_path is None:
        for candidate in DEFAULT_CONFIG_PATHS:
            if candidate.exists():
                config_path = candidate
                break
    if config_path and config_path.exists():
        logger.debug("Loading config from %s", config_path)
        raw = _load_toml(config_path)

    backoff = _parse_backoff(raw.get("backoff", {}))
    alerts = _parse_alerts(raw.get("alerts", {}))

    cfg = RetryCtlConfig(
        max_attempts=int(os.environ.get("RETRYCTL_MAX_ATTEMPTS", raw.get("max_attempts", 3))),
        backoff=backoff,
        alerts=alerts,
        shell=os.environ.get("RETRYCTL_SHELL", raw.get("shell", "/bin/sh")),
        capture_output=bool(raw.get("capture_output", True)),
    )
    return cfg
