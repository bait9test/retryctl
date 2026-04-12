"""Signal handling for retryctl — catch SIGINT/SIGTERM and mark runs as interrupted."""
from __future__ import annotations

import signal
import logging
from dataclasses import dataclass, field
from typing import Callable, Optional

log = logging.getLogger(__name__)


@dataclass
class SignalConfig:
    """Configuration for signal handling behaviour."""
    handle_sigint: bool = True
    handle_sigterm: bool = True
    propagate: bool = True  # re-raise / propagate to subprocess

    @classmethod
    def from_dict(cls, data: dict) -> "SignalConfig":
        if not isinstance(data, dict):
            raise TypeError(f"SignalConfig expects a dict, got {type(data).__name__}")
        return cls(
            handle_sigint=bool(data.get("handle_sigint", True)),
            handle_sigterm=bool(data.get("handle_sigterm", True)),
            propagate=bool(data.get("propagate", True)),
        )


class SignalInterrupted(Exception):
    """Raised when a handled signal interrupts the retry loop."""
    def __init__(self, signum: int):
        self.signum = signum
        super().__init__(f"Interrupted by signal {signum}")


@dataclass
class SignalHandler:
    """Installs signal handlers and tracks whether an interrupt was received."""
    config: SignalConfig
    _interrupted: bool = field(default=False, init=False)
    _signum: Optional[int] = field(default=None, init=False)
    _original_handlers: dict = field(default_factory=dict, init=False)

    def install(self) -> None:
        """Install handlers for configured signals."""
        if self.config.handle_sigint:
            self._original_handlers[signal.SIGINT] = signal.signal(
                signal.SIGINT, self._handle
            )
        if self.config.handle_sigterm:
            self._original_handlers[signal.SIGTERM] = signal.signal(
                signal.SIGTERM, self._handle
            )
        log.debug("Signal handlers installed (sigint=%s, sigterm=%s)",
                  self.config.handle_sigint, self.config.handle_sigterm)

    def restore(self) -> None:
        """Restore original signal handlers."""
        for sig, handler in self._original_handlers.items():
            signal.signal(sig, handler)
        self._original_handlers.clear()
        log.debug("Signal handlers restored")

    def _handle(self, signum: int, _frame) -> None:
        log.warning("Received signal %d — flagging interrupt", signum)
        self._interrupted = True
        self._signum = signum

    @property
    def interrupted(self) -> bool:
        return self._interrupted

    @property
    def signum(self) -> Optional[int]:
        return self._signum

    def raise_if_interrupted(self) -> None:
        """Raise SignalInterrupted if a signal was received."""
        if self._interrupted and self._signum is not None:
            raise SignalInterrupted(self._signum)

    def __enter__(self) -> "SignalHandler":
        self.install()
        return self

    def __exit__(self, *_) -> None:
        self.restore()
