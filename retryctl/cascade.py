"""Cascade config — chain multiple commands so the next runs only if the
previous one failed (or succeeded, depending on mode)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Literal


@dataclass
class CascadeStep:
    command: str
    on: Literal["failure", "success", "always"] = "failure"


@dataclass
class CascadeConfig:
    enabled: bool = False
    steps: List[CascadeStep] = field(default_factory=list)
    stop_on_success: bool = True

    @staticmethod
    def from_dict(raw: dict) -> "CascadeConfig":
        if not isinstance(raw, dict):
            raise TypeError(f"cascade config must be a dict, got {type(raw).__name__}")

        steps_raw = raw.get("steps", [])
        if not isinstance(steps_raw, list):
            raise TypeError("cascade.steps must be a list")

        steps: List[CascadeStep] = []
        for item in steps_raw:
            if not isinstance(item, dict):
                raise TypeError("each cascade step must be a dict")
            cmd = item.get("command", "")
            if not cmd:
                raise ValueError("each cascade step must have a non-empty 'command'")
            on = item.get("on", "failure")
            if on not in ("failure", "success", "always"):
                raise ValueError(f"cascade step 'on' must be failure/success/always, got {on!r}")
            steps.append(CascadeStep(command=cmd, on=on))

        return CascadeConfig(
            enabled=bool(raw.get("enabled", len(steps) > 0)),
            steps=steps,
            stop_on_success=bool(raw.get("stop_on_success", True)),
        )


def should_run_step(step: CascadeStep, last_succeeded: bool) -> bool:
    """Return True if *step* should execute given the outcome of the previous command."""
    if step.on == "always":
        return True
    if step.on == "success":
        return last_succeeded
    return not last_succeeded  # "failure"


def run_cascade(config: CascadeConfig, last_succeeded: bool) -> List[str]:
    """Return the ordered list of commands that should run given *last_succeeded*.

    Respects *stop_on_success*: once a step would run and the caller marks it
    succeeded, subsequent steps that are mode='failure' are skipped.
    This function only does selection — actual execution is the caller's job.
    """
    if not config.enabled:
        return []

    selected: List[str] = []
    current_succeeded = last_succeeded
    for step in config.steps:
        if should_run_step(step, current_succeeded):
            selected.append(step.command)
            if config.stop_on_success and step.on in ("failure", "always"):
                # optimistically assume step succeeds for chaining purposes
                current_succeeded = True
    return selected
