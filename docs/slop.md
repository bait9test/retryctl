# Slop — Marginal Failure Tolerance

`slop` lets you define a set of *marginal* exit codes that are forgiven for
a configurable number of consecutive occurrences before being treated as
genuine failures.

This is useful when a command occasionally returns a known "soft" exit code
(e.g. `1` for a transient resource warning) that you want to absorb without
consuming your retry budget.

## Configuration

```toml
[slop]
enabled          = true
tolerance_codes  = [1, 75]   # exit codes treated as marginal
window           = 3         # how many marginal hits are forgiven
```

| Key               | Type        | Default | Description                                      |
|-------------------|-------------|---------|--------------------------------------------------|
| `enabled`         | bool        | `false` | Activate the slop feature.                       |
| `tolerance_codes` | list[int]   | `[]`    | Exit codes considered marginal.  Setting any code auto-enables slop. |
| `window`          | int (≥ 1)   | `3`     | Number of consecutive marginal failures forgiven.|

## Behaviour

1. After each failed attempt `retryctl` checks whether the exit code is in
   `tolerance_codes`.
2. If it is **and** the marginal counter is below `window`, the failure is
   *absorbed* — the retry counter is **not** incremented and the next attempt
   begins immediately.
3. Once the window is exhausted the marginal code is treated as a normal
   failure and the retry counter advances as usual.
4. A successful run resets the marginal counter.

## Example

```toml
[slop]
tolerance_codes = [1]
window          = 2
```

With this config, the first two consecutive `exit 1` results are silently
retried.  The third is counted against the retry budget.

## Notes

- `window` must be ≥ 1; a value of `0` raises a `ValueError` at load time.
- If `tolerance_codes` is non-empty and `enabled` is not explicitly set,
  `enabled` defaults to `true`.
- The slop counter is per-run (not persisted across process restarts).
