# retryctl

A CLI tool for retrying failed shell commands with configurable backoff and alerting.

---

## Installation

```bash
pip install retryctl
```

Or install from source:

```bash
git clone https://github.com/yourname/retryctl.git && cd retryctl && pip install .
```

---

## Usage

```bash
retryctl [OPTIONS] -- <command>
```

**Basic example** — retry up to 5 times with exponential backoff:

```bash
retryctl --attempts 5 --backoff exponential --delay 2 -- curl https://example.com/api
```

**With alerting** — send a notification if all retries fail:

```bash
retryctl --attempts 3 --backoff linear --alert slack --webhook $SLACK_WEBHOOK -- ./deploy.sh
```

### Options

| Flag | Description | Default |
|------|-------------|---------|
| `--attempts` | Number of retry attempts | `3` |
| `--delay` | Initial delay in seconds | `1` |
| `--backoff` | Backoff strategy (`fixed`, `linear`, `exponential`) | `fixed` |
| `--alert` | Alert provider on final failure (`slack`, `email`) | None |
| `--timeout` | Per-attempt timeout in seconds | None |

---

## License

This project is licensed under the [MIT License](LICENSE).