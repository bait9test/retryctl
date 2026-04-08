"""CLI entry point for retryctl."""

import argparse
import logging
import sys
from pathlib import Path
from typing import List, Optional

from retryctl.backoff import BackoffStrategy, BackoffConfig
from retryctl.alerts import AlertConfig, AlertChannel
from retryctl.config import RetryCtlConfig, load_config
from retryctl.runner import run_with_retry

logger = logging.getLogger("retryctl")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="retryctl",
        description="Retry failed shell commands with configurable backoff and alerting.",
    )
    p.add_argument("command", nargs=argparse.REMAINDER, help="Command to run")
    p.add_argument("-n", "--attempts", type=int, default=None, help="Max attempts")
    p.add_argument(
        "--strategy",
        choices=[s.value for s in BackoffStrategy],
        default=None,
        help="Backoff strategy",
    )
    p.add_argument("--base-delay", type=float, default=None, help="Base delay in seconds")
    p.add_argument("--max-delay", type=float, default=None, help="Max delay cap in seconds")
    p.add_argument("--jitter", action="store_true", default=None, help="Enable jitter")
    p.add_argument("--config", type=Path, default=None, help="Path to config file")
    p.add_argument(
        "--alert",
        choices=[c.value for c in AlertChannel],
        action="append",
        dest="alert_channels",
        help="Alert channel (repeatable)",
    )
    p.add_argument("--webhook-url", default=None, help="Webhook URL for alerts")
    p.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging")
    return p


def apply_cli_overrides(cfg: RetryCtlConfig, args: argparse.Namespace) -> RetryCtlConfig:
    if args.attempts is not None:
        cfg.max_attempts = args.attempts
    if args.strategy is not None:
        cfg.backoff.strategy = BackoffStrategy(args.strategy)
    if args.base_delay is not None:
        cfg.backoff.base_delay = args.base_delay
    if args.max_delay is not None:
        cfg.backoff.max_delay = args.max_delay
    if args.jitter:
        cfg.backoff.jitter = True
    if args.alert_channels:
        cfg.alerts.channels = [AlertChannel(c) for c in args.alert_channels]
    if args.webhook_url:
        cfg.alerts.webhook_url = args.webhook_url
    return cfg


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(message)s",
    )

    command = [a for a in (args.command or []) if a != "--"]
    if not command:
        parser.print_help()
        return 2

    cfg = load_config(args.config)
    cfg = apply_cli_overrides(cfg, args)

    result = run_with_retry(
        command=command,
        max_attempts=cfg.max_attempts,
        backoff_cfg=cfg.backoff,
        alert_cfg=cfg.alerts,
        shell=cfg.shell,
    )

    if not result.succeeded:
        logger.error(
            "Command failed after %d attempt(s). Last exit code: %s",
            result.attempts,
            result.exit_code,
        )
        return result.exit_code or 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
