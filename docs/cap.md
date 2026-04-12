# Attempt Cap

The **attempt cap** middleware enforces a hard upper bound on the total number
of times retryctl will execute a command — across all retry cycles.

This is distinct from the per-run `max_retries` setting: the cap is a
*lifetime* guard that persists for the duration of a single `retryctl run`
invocation.

## Configuration

Add a `[cap]` table to your `retryctl.toml`:

```toml
[cap]
max_attempts = 10   # hard ceiling on total attempts
per_key      = false  # set true to scope the cap per label/key
```

| Key            | Type    | Default | Description                                      |
|----------------|---------|---------|--------------------------------------------------|
| `max_attempts` | integer | —       | Maximum attempts allowed. Enables cap implicitly.|
| `per_key`      | bool    | `false` | Scope the counter to the job label instead of globally. |
| `enabled`      | bool    | auto    | Explicitly enable/disable. Auto-enabled when `max_attempts` is set. |

## Behaviour

1. Before each attempt, `enforce_cap_gate` checks the running counter.
2. If the counter is **below** `max_attempts` the attempt proceeds and
   `on_attempt_consumed` increments the counter.
3. Once the counter reaches `max_attempts`, `CapExceeded` is raised and
   the retry loop exits immediately — no further attempts are made.

## Per-key scoping

When `per_key = true` each unique label (set via `[label]`) maintains its own
counter. This is useful when a single retryctl config drives multiple named
jobs in parallel.

## CLI override

```
retryctl run --cap-max 5 -- my-command
```

## Example

```toml
[label]
name = "db-migration"

[cap]
max_attempts = 3
```

With this config retryctl will attempt `db-migration` at most **3 times** in
total, regardless of the backoff schedule.
