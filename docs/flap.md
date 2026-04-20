# Flap Detection

Flap detection prevents retryctl from endlessly retrying a command that
alternates rapidly between success and failure ("flapping"). When the number
of outcome *transitions* within a rolling time window exceeds a threshold,
`FlapDetected` is raised and the retry loop is aborted.

## Configuration

```toml
[flap]
enabled = true
threshold = 4          # transitions within the window before aborting
window_seconds = 60.0  # rolling window size in seconds
```

`enabled` defaults to `true` whenever `threshold` is explicitly provided.

## How it works

A *transition* is counted whenever the outcome of one attempt differs from
the previous attempt (fail→pass or pass→fail). The tracker keeps a sliding
window of transition timestamps; once the count reaches `threshold` the run
is aborted with a `FlapDetected` exception.

## Example

```toml
[flap]
threshold = 3
window_seconds = 30
```

With this config, if a command succeeds, fails, succeeds, and fails again
within 30 seconds, retryctl will stop retrying and report flap detection.

## Notes

- Each unique command key maintains its own tracker across the process lifetime.
- Disable explicitly with `enabled = false` if you want to suppress detection
  even when a threshold is set.
