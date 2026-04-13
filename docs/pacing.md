# Pacing

Pacing enforces a **minimum wall-clock interval** between successive retry
attempts.  Unlike backoff (which adds deliberate delay *after* a failure),
pacing ensures that even fast-failing commands cannot hammer a downstream
resource faster than the configured floor.

## Configuration

```toml
[pacing]
enabled         = true
min_interval_s  = 2.0   # seconds between attempt starts
```

| Key | Type | Default | Description |
|---|---|---|---|
| `enabled` | bool | `false` | Enable pacing. Auto-enabled when `min_interval_s` > 0. |
| `min_interval_s` | float | `1.0` | Minimum seconds that must elapse between the *start* of one attempt and the *start* of the next. |

## How it works

1. Immediately before each attempt the middleware calls `before_attempt()`.
2. If the previous attempt finished sooner than `min_interval_s` ago,
   `PacingTracker.wait_if_needed()` sleeps for the remaining gap.
3. After sleeping (or not), the tracker records the new attempt start time.
4. On run completion (`on_run_complete`) the tracker is reset so that
   subsequent independent runs are unaffected.

## Interaction with backoff

Pacing and backoff are **additive**: backoff delay is applied first (by the
core runner), then pacing enforces the floor on top.  If backoff already
produces a delay longer than `min_interval_s` the pacing sleep is zero.

## Example

```toml
[retry]
max_attempts = 5

[backoff]
strategy = "exponential"
base_delay_s = 0.5

[pacing]
enabled        = true
min_interval_s = 3.0
```

With this config no two attempts will start less than 3 seconds apart,
regardless of how quickly the command exits.
