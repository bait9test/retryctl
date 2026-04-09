"""Desktop / system notification support for retryctl."""
from __future__ import annotations

import logging
import shutil
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

log = logging.getLogger(__name__)


class NotifyLevel(str, Enum):
    ALWAYS = "always"       # notify on every final outcome
    FAILURE = "failure"     # notify only when all retries exhausted
    NEVER = "never"         # notifications disabled


@dataclass
class NotifyConfig:
    level: NotifyLevel = NotifyLevel.NEVER
    title: str = "retryctl"
    sound: bool = False
    extra_args: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> "NotifyConfig":
        level = NotifyLevel(data.get("level", NotifyLevel.NEVER.value))
        return cls(
            level=level,
            title=data.get("title", "retryctl"),
            sound=bool(data.get("sound", False)),
            extra_args=list(data.get("extra_args", [])),
        )


def _notifier_cmd() -> Optional[str]:
    """Return the first available desktop notifier binary, or None."""
    for binary in ("notify-send", "terminal-notifier", "osascript"):
        if shutil.which(binary):
            return binary
    return None


def send_notification(cfg: NotifyConfig, message: str, success: bool) -> bool:
    """Send a desktop notification.  Returns True if the command succeeded."""
    if cfg.level == NotifyLevel.NEVER:
        return False
    if cfg.level == NotifyLevel.FAILURE and success:
        return False

    binary = _notifier_cmd()
    if binary is None:
        log.warning("notify: no supported notifier binary found; skipping")
        return False

    try:
        cmd = _build_cmd(binary, cfg, message)
        subprocess.run(cmd, check=True, timeout=5)
        log.debug("notify: sent notification via %s", binary)
        return True
    except Exception as exc:  # noqa: BLE001
        log.warning("notify: failed to send notification: %s", exc)
        return False


def _build_cmd(binary: str, cfg: NotifyConfig, message: str) -> list[str]:
    if binary == "notify-send":
        cmd = ["notify-send", cfg.title, message]
        if cfg.sound:
            cmd += ["--urgency", "critical"]
    elif binary == "terminal-notifier":
        cmd = ["terminal-notifier", "-title", cfg.title, "-message", message]
        if cfg.sound:
            cmd += ["-sound", "default"]
    else:  # osascript fallback
        script = f'display notification "{message}" with title "{cfg.title}"'
        cmd = ["osascript", "-e", script]
    return cmd + list(cfg.extra_args)
