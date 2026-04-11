"""Middleware helpers for wiring TraceConfig into the retry pipeline."""
from __future__ import annotations

from typing import Optional

from retryctl.trace import (
    TraceConfig,
    TraceContext,
    inject_trace_env,
    new_trace,
    write_trace_record,
)


def parse_trace(raw_cfg: dict) -> TraceConfig:
    """Extract and validate the [trace] section from a raw config dict."""
    section = raw_cfg.get("trace", {})
    if not isinstance(section, dict):
        raise TypeError(f"[trace] must be a table, got {type(section).__name__}")
    return TraceConfig.from_dict(section)


def trace_config_to_dict(cfg: TraceConfig) -> dict:
    return {
        "enabled": cfg.enabled,
        "trace_id": cfg.trace_id,
        "output_file": cfg.output_file,
        "env_prefix": cfg.env_prefix,
    }


def setup_trace(
    cfg: TraceConfig,
    base_env: Optional[dict] = None,
) -> tuple[Optional[TraceContext], dict]:
    """Initialise tracing for a run.

    Returns ``(ctx, env)`` where *ctx* is ``None`` when tracing is disabled
    and *env* is the (possibly augmented) environment mapping to pass to the
    subprocess.
    """
    env = dict(base_env or {})
    if not cfg.enabled:
        return None, env

    ctx = new_trace(cfg)
    env = inject_trace_env(cfg, ctx, env)
    return ctx, env


def finalise_trace(cfg: TraceConfig, ctx: Optional[TraceContext]) -> None:
    """Write the trace record if an output file is configured."""
    if not cfg.enabled or ctx is None:
        return
    if cfg.output_file:
        write_trace_record(ctx, cfg.output_file)
