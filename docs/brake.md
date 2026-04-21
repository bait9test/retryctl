# Brake

The **brake** feature adds progressively increasing delay to retry attempts
when consecutive failures accumulate beyond a configurable threshold.  It is
distinct from the standard backoff strategy — backoff controls the base
inter-attempt wait, while brake *adds* an extra penalty on top of whatever
delay the backoff strategy already computed.

## Configuration

```toml
[brake]
enabled   = true
threshold = 3      # failures before braking starts (default 3)
step_ms   = 500    # ms added per failure beyond threshold (default 500)
max_ms    = 10000  # ceiling on the extra delay (default 10 000)
```

| Key         | Type    | Default  | Description                                          |
|-------------|---------|----------|------------------------------------------------------|
| `enabled`   | bool    | `false`  | Enable the brake feature.                            |
| `threshold` | integer | `3`      | Consecutive failures before extra delay is applied.  |
| `step_ms`   | integer | `500`    | Milliseconds added per failure above the threshold.  |
| `max_ms`    | integer | `10000`  | Maximum extra delay in milliseconds.                 |

## Behaviour

1. retryctl counts consecutive failures for the current run.
2. Once the count exceeds `threshold`, each subsequent failure adds `step_ms`
   to a running penalty, capped at `max_ms`.
3. The penalty is applied **in addition** to the normal backoff delay before
   the next attempt.
4. Any successful attempt resets the penalty to zero.

## Example

With `threshold=2`, `step_ms=300`, `max_ms=900`:

| Attempt | Outcome | Consecutive failures | Extra delay |
|---------|---------|----------------------|-------------|
| 1       | fail    | 1                    | 0 ms        |
| 2       | fail    | 2                    | 0 ms        |
| 3       | fail    | 3                    | 300 ms      |
| 4       | fail    | 4                    | 600 ms      |
| 5       | fail    | 5                    | 900 ms (cap)|
| 6       | success | 0                    | reset        |

## Notes

- Setting `step_ms = 0` disables the accumulation effect while keeping the
  feature enabled (useful for testing).
- The brake state is **per-run** and is not persisted across process restarts.
- Combine with `[circuit]` to hard-stop after a sustained failure run.
