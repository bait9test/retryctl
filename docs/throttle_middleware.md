# Throttle Middleware

The `throttle` feature serialises concurrent executions of the same logical
job by acquiring a file-system lock before each run.  It is built on top of
`ThrottleLock` from `retryctl/throttle.py`.

## Configuration

Add a `[throttle]` section to your `retryctl.toml`:

```toml
[throttle]
enabled   = true
key       = "deploy-prod"      # logical name for the lock
lock_dir  = "/var/lock/retryctl"  # directory for lock files (default: /tmp/retryctl/throttle)
timeout   = 30                 # seconds to wait before giving up (default: 30)
```

### Auto-enable

Setting `key` without an explicit `enabled` flag will automatically enable
the throttle.  Set `enabled = false` explicitly to override this.

## Behaviour

- When enabled, `retryctl` attempts to acquire a lock identified by `key`
  before running the command.
- If the lock cannot be acquired within `timeout` seconds the run is aborted
  and a non-zero exit code is returned.
- The lock is released when the run finishes (success **or** failure).
- Different `key` values are independent — two jobs with distinct keys can
  run concurrently.

## CLI override

```
retryctl --throttle-key deploy-prod --throttle-timeout 60 -- ./deploy.sh
```

## Relationship to `concurrency`

The `throttle` middleware uses an exclusive file lock (blocking with a
timeout), while `concurrency` uses a non-blocking lock and fails
immediately.  Use `throttle` when you want callers to *wait* rather than
fail fast.
