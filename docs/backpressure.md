# Backpressure

The backpressure feature lets `retryctl` slow itself down automatically when
the host is under load.  Before each retry attempt the current load value is
sampled; if it exceeds a configured threshold the attempt is delayed by an
extra *penalty* sleep.

## Configuration

Add a `[backpressure]` section to your `retryctl.toml`:

```toml
[backpressure]
# Read load from a file (first whitespace-delimited token on the first line).
source_file = "/proc/loadavg"

# OR run a shell command and parse its stdout as a float.
# source_cmd = "cat /sys/fs/cgroup/cpu.stat | awk '/nr_throttled/{print $2}'"

# Pause retries when load exceeds this value.
threshold = 2.0

# Base penalty in seconds (scaled linearly with load/threshold ratio).
penalty_seconds = 5.0

# Never sleep longer than this, regardless of load.
max_penalty_seconds = 60.0
```

> **Note:** `source_file` and `source_cmd` are mutually exclusive.
> Setting either one automatically enables backpressure without needing
> `enabled = true`.

## How the penalty is calculated

```
ratio   = current_load / threshold
penalty = min(penalty_seconds * ratio, max_penalty_seconds)
```

So if `threshold = 1.0`, `penalty_seconds = 5.0`, and the measured load is
`4.0`, the penalty will be **20 seconds** (capped at `max_penalty_seconds`).

## Disabling

```toml
[backpressure]
enabled = false
```

Or simply omit the section entirely — backpressure is **disabled by default**.

## CLI override

Backpressure can be disabled at run time without editing the config file:

```bash
retryctl --no-backpressure -- my-command
```
