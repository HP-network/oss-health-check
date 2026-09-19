# OSS Health Check

[![Tests](https://github.com/HP-network/oss-health-check/actions/workflows/ci.yml/badge.svg)](https://github.com/HP-network/oss-health-check/actions/workflows/ci.yml)

Small, dependency-free checks for the things that make a repository easier to publish, review, and maintain.

`oss-health-check` is intentionally local-first. It does not upload source code, call an LLM, or require a GitHub token. Run it before making a project public, or use the composite action on every pull request.

## What it checks

- README, license, contribution guide, security policy, and code of conduct
- GitHub Actions workflows and `.gitignore`
- obvious test directories and common project metadata
- Git working-tree state and tracked-file count
- common private-key and token patterns in tracked text files
- tracked files larger than 5 MiB

The score is a prioritization aid, not a security certification. Secret detection is deliberately conservative and should be followed by a proper secret scanner for production use.

## Install and use

Requires Python 3.10 or newer.

```sh
python -m pip install oss-health-check
oss-health-check .
oss-health-check . --format markdown > health-report.md
oss-health-check . --format json > health-report.json
oss-health-check . --strict
```

`--strict` exits with status 1 when a possible secret is detected. Other warnings remain visible without making a normal run fail.

## GitHub Action

```yaml
name: Repository health

on:
  pull_request:
  push:

jobs:
  health:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: HP-network/oss-health-check@v1
```

The action appends a Markdown report to the job summary. Set `strict: 'false'` when the report is informational only.

## Development

```sh
python -m unittest discover -s tests
python -m oss_health_check . --format markdown
```

## License

MIT
