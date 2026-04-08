"""Core retry runner — executes a shell command with retries and backoff."""

import subprocess
import time
from dataclasses import dataclass, field
from typing import List, Optional

from retryctl.backoff import BackoffConfig, delay_sequence


@dataclass
class RetryResult:
    command: List[str]
    attempts: int
    succeeded: bool
    exit_code: int
    delays: List[float] = field(default_factory=list)
    stdout: str = ""
    stderr: str = ""


def run_with_retry(
    command: List[str],
    max_attempts: int = 3,
    backoff: Optional[BackoffConfig] = None,
    timeout: Optional[float] = None,
) -> RetryResult:
    """Run a shell command, retrying on non-zero exit codes."""
    if backoff is None:
        backoff = BackoffConfig()

    delays_used: List[float] = []
    delays = delay_sequence(backoff)
    last_result = None

    for attempt in range(1, max_attempts + 1):
        try:
            proc = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired as exc:
            last_result = RetryResult(
                command=command,
                attempts=attempt,
                succeeded=False,
                exit_code=-1,
                delays=delays_used,
                stderr=f"Timed out after {timeout}s",
            )
        else:
            last_result = RetryResult(
                command=command,
                attempts=attempt,
                succeeded=proc.returncode == 0,
                exit_code=proc.returncode,
                delays=delays_used,
                stdout=proc.stdout,
                stderr=proc.stderr,
            )
            if last_result.succeeded:
                return last_result

        if attempt < max_attempts:
            delay = next(delays)
            delays_used.append(delay)
            time.sleep(delay)

    return last_result
