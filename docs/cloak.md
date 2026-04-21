# Cloak

The **cloak** feature probabilistically masks individual retry attempts from
downstream observers (metrics, alerts, audit logs) without actually skipping
execution.  This is useful when you want to reduce noise in dashboards during
known-flaky periods while still running the command normally.

## Configuration

```toml
[cloak]
enabled   = true
mask_rate = 0.3      # 30 % of attempts are marked as cloaked
tag       = "cloaked"  # label attached to masked attempts
seed      = 42         # optional – makes behaviour reproducible
```

| Key         | Type    | Default     | Description |
|-------------|---------|-------------|-------------|
| `enabled`   | bool    | `false`     | Activate the feature. Auto-enabled when `mask_rate > 0`. |
| `mask_rate` | float   | `0.0`       | Probability (0–1) that any given attempt is cloaked. |
| `tag`       | string  | `"cloaked"` | Label stored on masked attempts for filtering. |
| `seed`      | integer | `null`      | RNG seed for reproducible results (testing). |

## Behaviour

- A `CloakTracker` is created once per run and shares an RNG instance across
  all attempts so the seed is honoured correctly.
- `before_attempt()` is called at the start of each attempt.  If the attempt
  is selected for cloaking a `CloakedAttempt` exception is raised; the caller
  is responsible for catching it and deciding how to handle the attempt.
- Cloaked attempts are **still executed** — only their visibility to
  metrics/alerting pipelines is suppressed.
- `CloakTracker.cloaked_attempts` returns the list of attempt numbers that
  were masked during the current run.

## Example

```python
from retryctl.cloak import CloakConfig, CloakTracker, CloakedAttempt

cfg = CloakConfig(enabled=True, mask_rate=0.25, seed=7)
tracker = CloakTracker(cfg)

for attempt in range(1, 6):
    try:
        tracker.before_attempt(attempt)  # raises CloakedAttempt ~25 % of the time
        print(f"attempt {attempt} visible")
    except CloakedAttempt:
        print(f"attempt {attempt} masked")
```
