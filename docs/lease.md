# Lease Guard

The **lease** feature ensures that only one instance of a command runs at a time
by holding a time-bounded lock file before execution begins.

## Configuration

```toml
[lease]
enabled      = true
key          = "deploy-prod"   # unique name for this lease
ttl_seconds  = 60             # how long the lease is valid
lease_dir    = "/tmp/retryctl/leases"  # where lease files are stored
```

`enabled` is automatically set to `true` when a `key` is provided.

## Behaviour

1. Before the first attempt, `retryctl` tries to acquire a lease file at
   `<lease_dir>/<key>.lease`.
2. If a valid (non-expired) lease file already exists, a `LeaseHeld` error is
   raised and the run is aborted.
3. If the existing lease has expired it is silently reclaimed.
4. The lease file is always removed when the run finishes — whether it succeeds,
   fails, or raises an unexpected exception.

## Use Cases

- Prevent two cron jobs from running the same deployment simultaneously.
- Guard a resource-intensive task that should never overlap.
- Combine with `[cooldown]` to enforce both a minimum gap *and* mutual exclusion.

## Lease File Format

```json
{"pid": 12345, "expires_at": 1710000060.0}
```

The `pid` field is informational; expiry is determined solely by `expires_at`.

## CLI Override

```
retryctl --lease-key deploy-prod --lease-ttl 120 -- ./deploy.sh
```
