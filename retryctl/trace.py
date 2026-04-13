"""Distributed tracing support for retryctl.

Injects trace/span IDs into the subprocess environment and optionally
writes a trace record to a file for downstream consumers.
"""
from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class TraceConfig:
    enabled: bool = False
    trace_id: Optional[str] = None  # generated if None
    output_file: Optional[str] = None  # write JSON trace record here
    env_prefix: str = "RETRYCTL"

    @staticmethod
    def from_dict(data: dict) -> "TraceConfig":
        if not isinstance(data, dict):
            raise TypeError(f"TraceConfig expects a dict, got {type(data).__name__}")
        enabled = bool(data.get("enabled", False))
        trace_id = data.get("trace_id") or None
        output_file = data.get("output_file") or None
        prefix = str(data.get("env_prefix", "RETRYCTL"))
        return TraceConfig(
            enabled=enabled,
            trace_id=trace_id,
            output_file=output_file,
            env_prefix=prefix,
        )


@dataclass
class TraceContext:
    trace_id: str
    span_id: str
    started_at: float = field(default_factory=time.time)

    def to_env(self, prefix: str = "RETRYCTL") -> dict[str, str]:
        return {
            f"{prefix}_TRACE_ID": self.trace_id,
            f"{prefix}_SPAN_ID": self.span_id,
        }

    def to_dict(self) -> dict:
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "started_at": self.started_at,
        }

    def elapsed(self) -> float:
        """Return the number of seconds elapsed since this context was created."""
        return time.time() - self.started_at


def new_trace(cfg: TraceConfig) -> TraceContext:
    """Create a fresh TraceContext, reusing cfg.trace_id if provided."""
    trace_id = cfg.trace_id or str(uuid.uuid4())
    span_id = str(uuid.uuid4())
    return TraceContext(trace_id=trace_id, span_id=span_id)


def write_trace_record(ctx: TraceContext, path: str, extra: Optional[dict] = None) -> None:
    """Append a JSON trace record to *path*.

    Args:
        ctx: The trace context to record.
        path: Filesystem path to append the record to.
        extra: Optional dict of additional fields to merge into the record.
    """
    record = ctx.to_dict()
    record["written_at"] = time.time()
    record["elapsed"] = ctx.elapsed()
    if extra:
        record.update(extra)
    dest = Path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("a") as fh:
        fh.write(json.dumps(record) + "\n")


def inject_trace_env(cfg: TraceConfig, ctx: TraceContext, base: dict) -> dict:
    """Return a copy of *base* with trace variables merged in."""
    merged = dict(base)
    merged.update(ctx.to_env(cfg.env_prefix))
    return merged
