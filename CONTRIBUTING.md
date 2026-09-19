# Contributing

## Development

The project uses only the Python standard library at runtime. Run the test suite before opening a pull request:

```sh
PYTHONPATH=src python -m unittest discover -s tests -v
PYTHONPATH=src python -m oss_health_check . --format markdown
```

Keep checks deterministic and local. Do not add network calls or upload repository contents without a separate design discussion.

## Pull requests

Explain the behavior change, include a regression test, and keep the command-line output backwards compatible when possible.
