"""Middleware helpers for integrating lease guards into the retry loop."""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Generator

from retryctl.lease import LeaseConfig, LeaseHeld, acquire_lease, release_lease

log = logging.getLogger(__name__)


def parse_lease(raw: dict) -> LeaseConfig:
    """Parse the [lease] section from a config dict."""
    section = raw.get("lease", {})
    if not isinstance(section, dict):
        raise TypeError(f"[lease] must be a table, got {type(section).__name__}")
    return LeaseConfig.from_dict(section)


def lease_config_to_dict(cfg: LeaseConfig) -> dict:
    return {
        "enabled": cfg.enabled,
        "ttl_seconds": cfg.ttl_seconds,
        "key": cfg.key,
        "lease_dir": cfg.lease_dir,
    }


@contextmanager
def run_with_lease(cfg: LeaseConfig) -> Generator[None, None, None]:
    """Context manager that acquires a lease before the block and releases it after.

    Raises LeaseHeld if the lease cannot be acquired.
    """
    if not cfg.enabled:
        yield
        return

    path = acquire_lease(cfg)
    try:
        yield
    finally:
        release_lease(path)


def describe_lease(cfg: LeaseConfig) -> str:
    if not cfg.enabled:
        return "lease: disabled"
    return f"lease: key='{cfg.key}' ttl={cfg.ttl_seconds}s dir={cfg.lease_dir}"
