"""Middleware helpers for the file-lock throttle feature."""
from __future__ import annotations

from typing import Any

from retryctl.throttle import ThrottleConfig

_DEFAULTS: dict[str, Any] = {
    "enabled": False,
    "key": None,
    "lock_dir": "/tmp/retryctl/throttle",
    "timeout": 30,
}


def parse_throttle(raw: dict[str, Any]) -> ThrottleConfig:
    """Build a ThrottleConfig from the [throttle] config section."""
    section = raw.get("throttle", {})
    if not isinstance(section, dict):
        raise TypeError(f"[throttle] must be a mapping, got {type(section).__name__}")

    key: str | None = section.get("key", _DEFAULTS["key"])
    lock_dir: str = section.get("lock_dir", _DEFAULTS["lock_dir"])
    timeout: int = int(section.get("timeout", _DEFAULTS["timeout"]))

    # Auto-enable when a key is provided
    default_enabled = bool(key)
    enabled: bool = bool(section.get("enabled", default_enabled))

    return ThrottleConfig(
        enabled=enabled,
        key=key,
        lock_dir=lock_dir,
        timeout=timeout,
    )


def throttle_config_to_dict(cfg: ThrottleConfig) -> dict[str, Any]:
    """Serialise a ThrottleConfig back to a plain dictionary."""
    return {
        "enabled": cfg.enabled,
        "key": cfg.key,
        "lock_dir": cfg.lock_dir,
        "timeout": cfg.timeout,
    }


def describe_throttle(cfg: ThrottleConfig) -> str:
    """Return a human-readable description of the throttle configuration."""
    if not cfg.enabled:
        return "throttle: disabled"
    key_label = cfg.key or "<default>"
    return (
        f"throttle: enabled | key={key_label} "
        f"lock_dir={cfg.lock_dir} timeout={cfg.timeout}s"
    )
