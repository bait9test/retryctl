# Splay

Splay introduces a randomised startup delay before the first attempt of a
command. This is useful in fleet environments where many hosts might trigger
the same retryctl job simultaneously — spreading the load avoids thundering-
herd problems on downstream services.

## Configuration

```toml
[splay]
enabled     = true
max_seconds = 10.0   # sleep a random duration in [0, 10] seconds
seed        = 42     # optional: fix the RNG seed (useful in tests)
```

`enabled` defaults to `true` when `max_seconds` is set to a positive value,
so the minimal config is just:

```toml
[splay]
max_seconds = 5.0
```

## CLI override

```
retryctl --splay-max 5 -- my-command
```

## Behaviour

- The delay is sampled uniformly from `[0, max_seconds]`.
- The sleep happens **once**, before the first attempt, not between retries
  (use `backoff` for inter-attempt delays).
- If `enabled = false` or `max_seconds = 0`, no sleep occurs.
- Setting `seed` makes the delay deterministic — handy for integration tests
  or when you want reproducible behaviour in CI.

## Example

Spread a cron-triggered health-check across a 30-second window:

```toml
[splay]
max_seconds = 30.0

[backoff]
strategy    = "exponential"
initial_ms  = 500
max_ms      = 30000
```
