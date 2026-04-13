# Development

## Environment Setup

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e .[dev]
```

Optional RF extras:

```bash
pip install -e .[rf]
```

## Main Commands

Validation:

```bash
mmm-studio validate
```

Scoring:

```bash
mmm-studio score --profile broadband --top-n 10
```

Demo pipeline:

```bash
mmm-studio run-demo --profile broadband --top-n 10 --output-dir artifacts/demo_run
```

Report export:

```bash
mmm-studio export-report --profile manufacturability_aware --output outputs/candidate_report.md
```

API:

```bash
uvicorn mmm_studio.api:app --reload
```

## Quality Gates

Format check:

```bash
ruff format --check .
```

Lint:

```bash
ruff check .
```

Type check:

```bash
mypy src
```

Test suite:

```bash
pytest
```

## Pre-commit

Install hooks:

```bash
pre-commit install
```

Run hooks manually:

```bash
pre-commit run --all-files
```

## Contributor Guidelines

- preserve the distinction between surrogate scoring and real simulation
- add or extend typed contracts before adding convenience wrappers
- keep optional dependencies behind explicit adapter boundaries
- update docs and tests with every nontrivial feature change
- prefer extending the existing architecture over adding parallel code paths
