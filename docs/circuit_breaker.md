# Circuit Breaker

The circuit breaker feature prevents a persistently-failing command from
being retried indefinitely.  After a configurable number of consecutive
failures the circuit *opens* and all further attempts are blocked until
a cool-down window has elapsed.

## Configuration

Add a `[circuit]` table to your `retryctl.toml`:

```toml
[circuit]
enabled            = true
failure_threshold  = 5      # open after this many consecutive failures
reset_seconds      = 60     # seconds before the circuit closes again
state_dir          = "/tmp/retryctl/circuit"  # where state files are stored
```

| Key | Type | Default | Description |
|---|---|---|---|
| `enabled` | bool | `false` | Enable the circuit breaker |
| `failure_threshold` | int | `5` | Consecutive failures before opening |
| `reset_seconds` | int | `60` | Seconds until the circuit auto-resets |
| `state_dir` | str | `/tmp/retryctl/circuit` | Directory for per-key state files |

## Behaviour

1. Before each attempt `enforce_circuit_gate` is called.  If the circuit
   is open a `CircuitOpen` exception is raised and the run is aborted.
2. After every failed attempt `on_attempt_failure` increments the failure
   counter.  When the counter reaches `failure_threshold` the circuit opens
   and the current timestamp is recorded.
3. After a successful run `on_run_success` resets the counter so that
   transient failures do not accumulate indefinitely.
4. State is persisted to a small JSON file under `state_dir` so the circuit
   survives process restarts.

## Key isolation

Each unique command key gets its own state file, so tripping the circuit
for one job never affects another.

## Example

```bash
# This will be blocked after 5 consecutive failures:
retryctl run --max-attempts 20 -- ./flaky-script.sh
```

When the circuit is open you will see:

```
CircuitOpen: circuit open for 'flaky-script.sh'; resets in 47s
```
