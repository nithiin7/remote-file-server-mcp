# Contributing

Thanks for taking the time to contribute.

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

## Setup

```bash
git clone https://github.com/nithin/remote-file-server-mcp.git
cd remote-file-server-mcp
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,docs]"
```

Or with uv:

```bash
uv sync --all-extras
```

## Running the tests

```bash
pytest
```

The test suite runs entirely against mock/fixture data — no live SMB server is required.

To run a specific file or test:

```bash
pytest tests/test_tools.py
pytest tests/test_validators.py -k "test_path_traversal"
```

Linting and type checks (run by CI):

```bash
ruff check .
ruff format --check .
```

## Commit message convention

This project follows [Conventional Commits](https://www.conventionalcommits.org/).

```
<type>(<scope>): <short summary>
```

Common types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`.

Examples:
- `feat(tools): add search_files max_results parameter`
- `fix(smb): handle reconnect on timeout`
- `docs: update Docker run example`

Releases and CHANGELOG entries are generated automatically from commit messages via
[release-please](https://github.com/googleapis/release-please), so following the
convention is important.

## Submitting a pull request

1. Fork the repo and create a branch from `main`.
2. Make your changes with appropriate tests.
3. Run `pytest` and `ruff check .` locally — CI will reject failures.
4. Open a PR against `main`. Fill in the pull request template.
5. A maintainer will review within a few days.

For non-trivial changes, open an issue first to discuss the approach.

## Security issues

Please do **not** open a public issue for security vulnerabilities. Follow the
process described in [SECURITY.md](SECURITY.md).
