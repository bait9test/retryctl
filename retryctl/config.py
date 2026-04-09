"""Configuration loading for retryctl."""

from __future__ import annotations

import os
import logging
from dataclasses import dataclass, field
from typing import Any

from retryctl.backoff import BackoffConfig, BackoffStrategy
from retryctl.alerts import AlertConfig, AlertChannel
from retryctl.ratelimit import RateLimitConfig

logger = logging.getLogger(__name__)


@dataclass
class RetryCtlConfig:
    max_attempts: int = 3
    backoff: BackoffConfig = field(default_factory=BackoffConfig)
    alerts: AlertConfig = field(default_factory=AlertConfig)
    rate_limit: RateLimitConfig = field(default_factory=RateLimitConfig)


def _load_toml(path: str) -> dict[str, Any]:
    try:
        import tomllib  # type: ignore
    except ImportError:
        try:
            import tomli as tomllib  # type: ignore
        except ImportError:
            return {}
    try:
        with open(path, "rb") as fh:
            return tomllib.load(fh)
    except FileNotFoundError:
        return {}


def _parse_backoff(raw: dict[str, Any]) -> BackoffConfig:
    strategy_str = raw.get("strategy", "fixed").upper()
    strategy = BackoffStrategy[strategy_str]
    return BackoffConfig(
        strategy=strategy,
        base_delay=float(raw.get("base_delay", 1.0)),
        max_delay=float(raw.get("max_delay", 60.0)),
        multiplier=float(raw.get("multiplier", 2.0)),
        jitter=bool(raw.get("jitter", False)),
    )


def _parse_alerts(raw: dict[str, Any]) -> AlertConfig:
    channel_str = raw.get("channel", "log").upper()
    channel = AlertChannel[channel_str]
    return AlertConfig(
        channel=channel,
        threshold=int(raw.get("threshold", 1)),
        email_to=raw.get("email_to", ""),
        webhook_url=raw.get("webhook_url", ""),
    )


def _parse_rate_limit(raw: dict[str, Any]) -> RateLimitConfig:
    return RateLimitConfig(
        max_attempts_per_window=int(raw.get("max_attempts_per_window", 0)),
        window_seconds=float(raw.get("window_seconds", 60.0)),
    )


def load_config(path: str = "retryctl.toml") -> RetryCtlConfig:
    """Load configuration from *path*, falling back to environment variables and defaults."""
    raw = _load_toml(path)

    max_attempts = int(
        os.environ.get("RETRYCTL_MAX_ATTEMPTS", raw.get("max_attempts", 3))
    )

    backoff_raw = raw.get("backoff", {})
    if "RETRYCTL_BACKOFF_STRATEGY" in os.environ:
        backoff_raw["strategy"] = os.environ["RETRYCTL_BACKOFF_STRATEGY"]

    alerts_raw = raw.get("alerts", {})
    if "RETRYCTL_ALERT_CHANNEL" in os.environ:
        alerts_raw["channel"] = os.environ["RETRYCTL_ALERT_CHANNEL"]

    rate_limit_raw = raw.get("rate_limit", {})
    if "RETRYCTL_RATE_LIMIT_MAX" in os.environ:
        rate_limit_raw["max_attempts_per_window"] = int(
            os.environ["RETRYCTL_RATE_LIMIT_MAX"]
        )

    return RetryCtlConfig(
        max_attempts=max_attempts,
        backoff=_parse_backoff(backoff_raw),
        alerts=_parse_alerts(alerts_raw),
        rate_limit=_parse_rate_limit(rate_limit_raw),
    )
