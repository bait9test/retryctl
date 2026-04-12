"""Hedged retry: launch a speculative duplicate attempt after a delay.

If the original attempt is still running after `delay_ms` milliseconds,
a second attempt is fired in parallel.  Whichever finishes first (with
any exit-code) wins; the other is cancelled.
"""
from __future__ import annotations

import subprocess
import threading
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class HedgeConfig:
    enabled: bool = False
    delay_ms: int = 500          # ms before the speculative attempt fires
    max_hedges: int = 1          # how many extra attempts may run in parallel

    def __post_init__(self) -> None:
        if self.delay_ms < 0:
            raise ValueError("hedge.delay_ms must be >= 0")
        if self.max_hedges < 1:
            raise ValueError("hedge.max_hedges must be >= 1")


def from_dict(data: dict) -> HedgeConfig:
    if not isinstance(data, dict):
        raise TypeError("hedge config must be a mapping")
    delay_ms = int(data.get("delay_ms", 500))
    max_hedges = int(data.get("max_hedges", 1))
    enabled = bool(data.get("enabled", delay_ms != 500 or max_hedges != 1))
    return HedgeConfig(enabled=enabled, delay_ms=delay_ms, max_hedges=max_hedges)


@dataclass
class HedgeResult:
    returncode: int
    stdout: bytes
    stderr: bytes
    winner_index: int            # 0 = original, 1+ = hedge attempt


def run_hedged(
    cmd: List[str],
    cfg: HedgeConfig,
    *,
    env: Optional[dict] = None,
    timeout: Optional[float] = None,
) -> HedgeResult:
    """Run *cmd* with at most cfg.max_hedges speculative duplicates."""
    result_holder: List[Optional[HedgeResult]] = [None]
    winner_event = threading.Event()
    lock = threading.Lock()
    procs: List[subprocess.Popen] = []

    def _run(index: int) -> None:
        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
            )
            with lock:
                procs.append(proc)
            stdout, stderr = proc.communicate(timeout=timeout)
            with lock:
                if not winner_event.is_set():
                    winner_event.set()
                    result_holder[0] = HedgeResult(
                        returncode=proc.returncode,
                        stdout=stdout,
                        stderr=stderr,
                        winner_index=index,
                    )
                    # cancel siblings
                    for p in procs:
                        if p is not proc:
                            try:
                                p.kill()
                            except OSError:
                                pass
        except Exception:
            pass

    threads = []
    t0 = threading.Thread(target=_run, args=(0,), daemon=True)
    threads.append(t0)
    t0.start()

    delay_s = cfg.delay_ms / 1000.0
    for i in range(cfg.max_hedges):
        winner_event.wait(timeout=delay_s)
        if winner_event.is_set():
            break
        t = threading.Thread(target=_run, args=(i + 1,), daemon=True)
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    if result_holder[0] is None:
        raise RuntimeError("hedge: all attempts failed to produce a result")
    return result_holder[0]
