"""Attempt cap middleware — hard limit on total lifetime retry attempts."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class CapConfig:
    """Configuration for a hard attempt cap."""
    enabled: bool = False
    max_attempts: Optional[int] = None  # None means unlimited
    per_key: bool = False               # scope cap per label/key rather than globally

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CapConfig":
        if not isinstance(data, dict):
            raise TypeError(f"CapConfig expects a dict, got {type(data).__name__}")
        max_attempts = data.get("max_attempts")
        if max_attempts is not None:
            max_attempts = int(max_attempts)
            if max_attempts < 1:
                raise ValueError("cap.max_attempts must be >= 1")
        enabled = bool(data.get("enabled", max_attempts is not None))
        per_key = bool(data.get("per_key", False))
        return cls(enabled=enabled, max_attempts=max_attempts, per_key=per_key)


class CapExceeded(Exception):
    """Raised when the attempt cap has been reached."""
    def __init__(self, key: str, limit: int) -> None:
        self.key = key
        self.limit = limit
        super().__init__(f"Attempt cap of {limit} reached for '{key}'")


@dataclass
class CapTracker:
    config: CapConfig
    _counts: Dict[str, int] = field(default_factory=dict)

    def _key(self, label: str) -> str:
        return label if self.config.per_key else "__global__"

    def is_allowed(self, label: str = "__global__") -> bool:
        if not self.config.enabled or self.config.max_attempts is None:
            return True
        k = self._key(label)
        return self._counts.get(k, 0) < self.config.max_attempts

    def consume(self, label: str = "__global__") -> None:
        if not self.config.enabled:
            return
        k = self._key(label)
        self._counts[k] = self._counts.get(k, 0) + 1

    def enforce(self, label: str = "__global__") -> None:
        """Consume one attempt and raise CapExceeded if the cap is now exceeded."""
        self.consume(label)
        k = self._key(label)
        if self.config.enabled and self.config.max_attempts is not None:
            if self._counts[k] > self.config.max_attempts:
                raise CapExceeded(label, self.config.max_attempts)

    def remaining(self, label: str = "__global__") -> Optional[int]:
        if not self.config.enabled or self.config.max_attempts is None:
            return None
        k = self._key(label)
        used = self._counts.get(k, 0)
        return max(0, self.config.max_attempts - used)
