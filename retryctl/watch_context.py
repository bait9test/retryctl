"""High-level loop that re-runs a callback each time watched files change."""
from __future__ import annotations

import logging
from typing import Callable, List, Optional

from retryctl.watch import WatchConfig, watch_for_change

log = logging.getLogger(__name__)


def run_watch_loop(
    cfg: WatchConfig,
    callback: Callable[[List[str]], None],
    *,
    _watch_fn: object = watch_for_change,  # injectable for tests
) -> None:
    """Repeatedly call *callback* with the list of changed paths.

    Stops after ``cfg.max_triggers`` invocations (or runs forever when None).
    """
    if not cfg.enabled:
        log.debug("watch loop disabled, skipping")
        return

    watch_fn = _watch_fn  # type: ignore[assignment]
    triggers = 0

    log.info("watching %d path(s): %s", len(cfg.paths), cfg.paths)

    while True:
        changed = watch_fn(cfg)
        triggers += 1
        log.info("[watch] trigger #%d — changed: %s", triggers, changed)

        try:
            callback(changed)
        except Exception as exc:  # noqa: BLE001
            log.warning("[watch] callback raised: %s", exc)

        if cfg.max_triggers is not None and triggers >= cfg.max_triggers:
            log.info("[watch] reached max_triggers=%d, stopping", cfg.max_triggers)
            break
