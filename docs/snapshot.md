# Snapshot

The **snapshot** feature records a hash of each attempt's output and detects
when it changes between retries. This is useful for commands whose output
should be stable (e.g. config generation, checksums) — a changing output
across attempts may indicate a flapping dependency.

## Configuration

```toml
[snapshot]
enabled          = true
path             = "/var/run/retryctl/snapshots"  # where to persist snapshot files
compare_stdout   = true   # hash stdout (default: true)
compare_stderr   = false  # hash stderr (default: false)
fail_on_change   = false  # treat output change as a hard failure
```

## Behaviour

- On every attempt retryctl computes a short SHA-256 hash of stdout and/or stderr.
- The hash is compared with the previous attempt's hash.
- If the output **changed**, a warning is logged.
- When `fail_on_change = true` the run is aborted immediately on a change.
- All snapshot entries are persisted as JSON under `path/` keyed by the
  sanitised command string so they survive across invocations.

## Example

```
$ retryctl --max-attempts 5 -- ./generate-config.sh
[retryctl] snapshot: output changed on attempt 3 for key 'generate-config.sh'
```

## Notes

- Snapshots are stored per command key; concurrent runs of different commands
  are isolated.
- The feature is **disabled by default** and has no overhead when off.
