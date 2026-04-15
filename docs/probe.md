# Probe

A **probe** is a lightweight health-check command that runs *before* each
attempt of the main command.  If the probe fails, retryctl can either skip
the attempt (and wait for the next backoff interval) or log a warning and
proceed anyway.

This is useful when the main command depends on an external service (database,
API, queue) that may be temporarily unavailable.

## Configuration

```toml
[probe]
enabled      = true
command      = ["curl", "-sf", "http://localhost:8080/healthz"]
timeout      = 5.0   # seconds per probe attempt
retries      = 2     # how many times to retry the probe itself
skip_on_fail = true  # skip the main attempt instead of aborting the run
```

| Key            | Type          | Default | Description |
|----------------|---------------|---------|-------------|
| `enabled`      | bool          | `false` | Activate the probe gate. Auto-set to `true` when `command` is provided. |
| `command`      | string / list | `[]`    | Shell command to run as the probe. |
| `timeout`      | float         | `5.0`   | Per-probe-attempt timeout in seconds. |
| `retries`      | int           | `1`     | Number of times to retry a failing probe before giving up. |
| `skip_on_fail` | bool          | `true`  | If `true`, skip the main attempt on probe failure. If `false`, log a warning and run anyway. |

## Behaviour

1. Before each attempt retryctl calls `check_probe(cfg)`.
2. The probe command is executed up to `retries` times with the given `timeout`.
3. If all probe attempts fail and `skip_on_fail = true`, a `ProbeSkip` exception
   is raised and the attempt is skipped (the backoff delay still applies).
4. If `skip_on_fail = false` the failure is logged and the main command runs
   regardless.

> **Note:** Probe retries are independent of the main command's retry counter.
> A skipped attempt still counts as one attempt toward the main command's
> `max_attempts` limit.

## Exit codes

The probe command is considered successful when it exits with code `0`.  Any
non-zero exit code (or a timeout) is treated as a failure.  If you need to
accept additional exit codes as success, wrap the command in a small shell
script that normalises the exit code before returning.

## Example

```toml
[probe]
command      = "pg_isready -h db -U app"
retries      = 3
timeout      = 2.0
skip_on_fail = true
```

With this configuration retryctl will verify that PostgreSQL is accepting
connections before each attempt.  If the database is not ready after three
probe tries the attempt is skipped and retryctl waits for the next backoff
window.
