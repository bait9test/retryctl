# Hedged Retries

A **hedged retry** fires a speculative duplicate of the current attempt after a
configurable delay.  Whichever copy finishes first wins; the other is
cancelled.  This trades a small amount of extra resource usage for a
significantly lower tail latency on flaky or slow commands.

## Configuration

```toml
[hedge]
enabled   = true
delay_ms  = 500   # ms to wait before launching the speculative attempt
max_hedges = 1    # maximum number of extra parallel attempts
```

| Key          | Type    | Default | Description                                      |
|--------------|---------|---------|--------------------------------------------------|
| `enabled`    | bool    | `false` | Enable hedging                                   |
| `delay_ms`   | integer | `500`   | Milliseconds before a speculative copy is fired  |
| `max_hedges` | integer | `1`     | How many extra copies may run simultaneously     |

## How it works

1. The original attempt starts immediately.
2. After `delay_ms` milliseconds, if it has not finished, a second copy of the
   command is launched.
3. This repeats up to `max_hedges` times.
4. The first copy to exit (regardless of exit code) is declared the winner.
   All remaining copies are sent `SIGKILL`.

## Example

```toml
[hedge]
enabled  = true
delay_ms = 300
```

With this config a command that normally takes ~200 ms will complete in ~200 ms.
A command that occasionally takes 2 s (due to a slow network hop) will almost
always complete in ~300 ms because the hedge fires and hits a different path.

## Caveats

- Hedging is only safe for **idempotent** commands.  Running the same write
  operation twice can corrupt state.
- Each hedge consumes an additional process slot and any associated I/O.
- `max_hedges` is intentionally capped to avoid runaway fan-out; keep it at 1
  or 2 for most use-cases.
