# Cordon

A **cordon** temporarily blocks all retry attempts for a command after it
fails too many times within a rolling time window. Unlike a circuit breaker
(which counts consecutive failures), the cordon counts *total* failures
within the window regardless of intervening successes.

## Configuration

```toml
[cordon]
enabled          = true
threshold        = 5       # failures before cordon is placed
window_seconds   = 60.0    # rolling window to count failures in
duration_seconds = 300.0   # how long the cordon stays active
key              = ""      # optional explicit key; defaults to command hash
```

## Behaviour

1. Every failed attempt increments a counter stored in a temp-dir JSON file.
2. Timestamps older than `window_seconds` are evicted before counting.
3. When the failure count reaches `threshold`, a cordon is placed that
   expires `duration_seconds` from now.  The failure list is then cleared.
4. While a cordon is active, `enforce_cordon_gate` raises `CordonBlocked`
   before the attempt even starts.
5. A successful overall run calls `on_run_success`, which removes the state
   file entirely.

## Difference from Circuit Breaker

| Feature        | Circuit Breaker          | Cordon                      |
|----------------|--------------------------|-----------------------------|
| Counts         | Consecutive failures     | Total failures in window    |
| Reset trigger  | Probe attempt succeeds   | Fixed duration expires      |
| Use-case       | Cascading-failure guard  | Noisy-command rate limiting |

## Middleware hooks

```python
from retryctl.cordon_middleware import (
    enforce_cordon_gate,   # call before each attempt
    on_attempt_failure,    # call after each failed attempt
    on_run_success,        # call when the run ultimately succeeds
)
```

## CLI override

```
--cordon-threshold 3 --cordon-window 30 --cordon-duration 120
```
