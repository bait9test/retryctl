# Canary Checks

A **canary check** is a lightweight command run *before* each retry attempt.
If the canary fails, the attempt is either skipped (default) or the whole run
is aborted immediately — without wasting resources on a doomed retry.

## Configuration

```toml
[canary]
enabled = true          # auto-enabled when `command` is set
command = ["curl", "-sf", "http://localhost:8080/health"]
timeout = 5.0           # seconds; must be > 0 (default: 5)
skip_on_failure = true  # false → raise CanaryBlocked and abort the run
```

`command` can also be a shell string:

```toml
command = "pg_isready -h db"
```

## Behaviour

| Canary result | `skip_on_failure = true` | `skip_on_failure = false` |
|---------------|--------------------------|---------------------------|
| Exit 0        | attempt proceeds         | attempt proceeds          |
| Non-zero      | attempt **skipped**      | run **aborted**           |
| Timeout       | attempt **skipped**      | run **aborted**           |

## Example — database readiness gate

```toml
[canary]
command = "pg_isready -h db -p 5432"
timeout = 3.0
skip_on_failure = true
```

Retryctl will silently skip any attempt while the database is unreachable and
retry again after the normal backoff delay.

## Example — hard dependency

```toml
[canary]
command = ["vault", "status"]
timeout = 2.0
skip_on_failure = false
```

If Vault is sealed or unreachable the run aborts immediately rather than
retrying indefinitely.

## CLI override

There is no dedicated CLI flag for the canary; configure it via the TOML
config file or the `RETRYCTL_CONFIG` environment variable.
