# Echo

The **echo** middleware caches the output of the last successful run and
replays it if the live command subsequently fails.  This is useful for
read-only reporting jobs where stale-but-present output is preferable to
a hard failure.

## Configuration

```toml
[echo]
enabled       = true
ttl_seconds   = 3600   # how long a cached entry remains valid (0 = forever)
cache_dir     = "/tmp/retryctl/echo"  # where cache files are stored
warn_on_echo  = true   # emit a warning log when cached output is returned
```

`enabled` is set automatically when `cache_dir` is provided.

## Behaviour

1. After every **successful** run `retryctl` writes `stdout` + `stderr` to a
   JSON file in `cache_dir`, keyed by the command string.
2. When a subsequent run **fails** (all retries exhausted), `retryctl` checks
   whether a valid cached entry exists.
3. If an entry is found and has not exceeded `ttl_seconds`, it is returned in
   place of the live failure.
4. If `warn_on_echo` is `true` a `WARNING` log line is emitted so operators
   know they are seeing replayed output.

## TTL

| `ttl_seconds` | Effect                              |
|---------------|-------------------------------------|
| `> 0`         | Entry expires after that many seconds |
| `0`           | Entry never expires                 |

## Example

```toml
[echo]
enabled      = true
ttl_seconds  = 1800
warn_on_echo = true
```

With this configuration a cached result stays valid for 30 minutes.  If the
command fails within that window the last known-good output is returned and a
warning is logged.

## Notes

- Cache files are plain JSON and can be inspected or deleted manually.
- Each command key is sanitised (non-alphanumeric characters replaced with
  `_`) and truncated to 80 characters before being used as a filename.
- The echo cache is independent of the checkpoint and state systems.
