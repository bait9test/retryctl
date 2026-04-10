"""Middleware that injects label information into subprocess environment.

When a LabelConfig is present, RETRYCTL_LABEL and individual
RETRYCTL_TAG_<KEY> variables are added to the child process environment
so that wrapped commands can inspect their own retry context.
"""

from __future__ import annotations

import os
from typing import Dict

from retryctl.label import LabelConfig


_ENV_LABEL_KEY = "RETRYCTL_LABEL"
_ENV_TAG_PREFIX = "RETRYCTL_TAG_"


def build_label_env(cfg: LabelConfig, base: Dict[str, str] | None = None) -> Dict[str, str]:
    """Return *base* (or a copy of ``os.environ``) augmented with label vars.

    Parameters
    ----------
    cfg:
        The label configuration to inject.
    base:
        Starting environment mapping.  Defaults to a copy of ``os.environ``.
    """
    env: Dict[str, str] = dict(base) if base is not None else dict(os.environ)

    if cfg.name:
        env[_ENV_LABEL_KEY] = cfg.name
    else:
        env.pop(_ENV_LABEL_KEY, None)

    # Remove any stale tag vars that may have been inherited.
    stale = [k for k in env if k.startswith(_ENV_TAG_PREFIX)]
    for k in stale:
        del env[k]

    for tag_key, tag_val in cfg.tags.items():
        env_key = _ENV_TAG_PREFIX + tag_key.upper().replace("-", "_")
        env[env_key] = tag_val

    return env
