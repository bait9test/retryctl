# Fallback Command

The `fallback` feature lets you specify an alternative command that runs
automatically when **all retries have been exhausted** and the primary command
has still not succeeded.

## Configuration

```toml
[fallback]
enabled = true          # auto-enabled when `command` is set
command = ["notify-admin", "--subject", "job failed"]
timeout = 10.0          # optional per-run timeout in seconds
capture_output = true   # capture stdout/stderr (default: true)
```

### Fields

| Field | Type | Default | Description |
|---|---|---|---|
| `enabled` | bool | `false` (auto `true` if command set) | Enable fallback execution |
| `command` | list\|string | `[]` | Command + arguments to run |
| `timeout` | float | `null` | Max seconds before the fallback is killed |
| `capture_output` | bool | `true` | Capture stdout/stderr from fallback |

## Behaviour

- The fallback command is **only executed when the primary run fails** (i.e.
  all retry attempts were exhausted without a zero exit code).
- A successful primary run **never** triggers the fallback.
- If the fallback itself exits non-zero, a warning is logged but `retryctl`
  still exits with the original failure code.
- Timeout and unexpected exceptions are caught and logged; they do not cause
  `retryctl` to crash.

## CLI override

You can supply a fallback command directly on the command line:

```sh
retryctl --fallback-cmd "notify-admin --subject 'job failed'" -- my-job.sh
```

## Example

```toml
[fallback]
command = ["curl", "-X", "POST", "https://hooks.example.com/alert"]
timeout = 5.0
```

This will POST to your webhook URL every time the retried command ultimately
fails.
