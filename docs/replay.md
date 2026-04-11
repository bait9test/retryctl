# Replay

The **replay** feature lets `retryctl` remember the last failed command so you
can re-run it later without having to retype the full invocation.

## Configuration

Add a `[replay]` table to your `retryctl.toml`:

```toml
[replay]
enabled     = true
replay_dir  = "/tmp/retryctl/replay"   # default
```

| Key          | Type   | Default                  | Description                          |
|--------------|--------|--------------------------|--------------------------------------|
| `enabled`    | bool   | `false`                  | Activate replay recording            |
| `replay_dir` | string | `/tmp/retryctl/replay`   | Directory where records are stored   |

## How it works

1. When a run **fails** (all retries exhausted), `retryctl` writes a JSON file
   to `replay_dir` named after the job label (or `default`).
2. On a subsequent **success** the record is automatically removed.
3. You can inspect or replay the last failure:

```bash
# Show the stored replay record
cat /tmp/retryctl/replay/myjob.json

# Re-run via retryctl (reads command from replay record)
retryctl replay --label myjob
```

## Record format

```json
{
  "command": ["./deploy.sh", "--env", "prod"],
  "exit_code": 1,
  "timestamp": 1718000000.0,
  "attempt_count": 3,
  "label": "myjob"
}
```

## Notes

- Records are plain JSON files — safe to inspect, copy, or version-control.
- The `replay_dir` is created automatically if it does not exist.
- When `enabled = false` (the default) no files are written or read.
