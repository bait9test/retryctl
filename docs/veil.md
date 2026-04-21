# veil — Probabilistic Attempt Suppression

`veil` lets you randomly drop a fraction of retry attempts based on a
configurable `drop_rate`.  This is useful for load-shedding in busy retry
loops where not every attempt needs to run.

## Configuration

```toml
[veil]
enabled   = true
drop_rate = 0.25   # drop 25 % of attempts at random
seed      = 42     # optional — fix the RNG for reproducible behaviour
```

| Key        | Type    | Default | Description                                        |
|------------|---------|---------|----------------------------------------------------|
| `enabled`  | bool    | `false` | Enable probabilistic suppression.                  |
| `drop_rate`| float   | `0.0`   | Fraction of attempts to drop (0.0 – 1.0). Setting a positive value auto-enables the feature. |
| `seed`     | integer | —       | Optional RNG seed for deterministic behaviour.     |

## Behaviour

- When `drop_rate = 0.0` or `enabled = false`, **no** attempts are dropped.
- When `drop_rate = 1.0`, **every** attempt is dropped (useful for testing).
- A dropped attempt raises `VeiledAttempt` internally; the retry loop treats
  this as a skipped iteration and does **not** count it against the retry
  budget.
- Setting `seed` makes the suppression deterministic across runs — handy for
  integration tests or canary deployments.

## Example

Drop half of all retry attempts while debugging a flaky service:

```toml
[veil]
drop_rate = 0.5
seed      = 7
```

## Notes

- The RNG state is **per-run**, not persisted across process restarts.
- Combine with `[budget]` or `[quota]` to ensure overall retry limits are
  still respected even when many attempts are veiled.
