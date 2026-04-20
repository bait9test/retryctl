# Taper

The **taper** feature gradually reduces the effective back-off delay multiplier
after a sustained run of consecutive failures.  This prevents runaway
exponential back-off in long-lived processes where a transient outage causes
dozens of failures before recovery.

## How it works

1. After each failed attempt the taper state machine increments an internal
   consecutive-failure counter.
2. Once the counter reaches `threshold` the multiplier is scaled by `factor`
   on every subsequent failure, down to a floor of `min_multiplier`.
3. When the run eventually succeeds the counter (and multiplier) are reset.

## Configuration

```toml
[taper]
enabled        = true
threshold      = 5        # failures before tapering kicks in
factor         = 0.75     # multiply current multiplier by this each time
min_multiplier = 0.1      # never go below this fraction of the base delay
reset_on_success = true   # reset state after a successful run
```

| Key               | Type    | Default | Description                                         |
|-------------------|---------|---------|-----------------------------------------------------|
| `enabled`         | bool    | `false` | Enable the taper feature                            |
| `threshold`       | int     | `5`     | Consecutive failures before tapering starts         |
| `factor`          | float   | `0.75`  | Multiplier applied to the delay multiplier each step|
| `min_multiplier`  | float   | `0.1`   | Floor for the delay multiplier                      |
| `reset_on_success`| bool    | `true`  | Reset the counter when the run succeeds             |

## Interaction with back-off

The taper multiplier is applied **on top of** the computed back-off delay:

```
effective_delay = compute_delay(attempt, backoff_cfg) * taper_multiplier
```

This means a fully-tapered run with `min_multiplier = 0.1` will wait at most
10 % of the normal exponential delay between retries.

## Example

```toml
[backoff]
strategy = "exponential"
base_delay = 2.0
max_delay  = 60.0

[taper]
enabled   = true
threshold = 4
factor    = 0.5
```

With this config, after 4 consecutive failures the retry delay is halved on
every further failure until it bottoms out at `min_multiplier * base_delay`.
