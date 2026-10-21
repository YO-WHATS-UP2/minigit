# Contributing

minigit welcomes contributions, especially small, focused improvements that help people learn how Git works.

## Before you start

1. Find an open issue that matches your interests.
2. Comment to claim it and wait until a mentor assigns it to you.
3. Read the [architecture guide](ARCHITECTURE.md) and, for command changes, the [first-command tutorial](adding-a-command.md).
4. Keep changes focused and add tests for behaviour changes.

## Run the checks

From the repository root:

```bash
pytest
ruff check .
ruff format --check .
mypy src/
```

## Preview this site

Install the optional documentation dependencies and start the local server:

```bash
pip install -e ".[docs]"
mkdocs serve
```

Open the local address printed by MkDocs, usually `http://127.0.0.1:8000/`. To catch broken links and configuration warnings before opening a pull request, run:

```bash
mkdocs build --strict
```

For the complete contribution and review process, see the repository's `CONTRIBUTING.md` on GitHub.
