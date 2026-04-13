# Contributing

## Principles

- keep the repository honest about what is simulated versus what is inferred
- preserve typed contracts at all external boundaries
- prefer extending existing modules over adding parallel architectures
- treat generated artifacts and provenance as part of the product, not disposable output

## Setup

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e .[dev]
```

Optional RF extras:

```bash
pip install -e .[rf]
```

## Before Opening a PR

Run:

```bash
ruff format --check .
ruff check .
mypy src
pytest
mmm-studio run-demo --profile broadband --top-n 5 --output-dir artifacts/pr-smoke
```

## Contribution Scope

Good contributions:

- typed model extensions
- validation coverage
- scoring/reporting improvements that stay explicit about surrogate status
- simulation or RF scaffolds that do not fabricate outputs
- docs, diagrams, tests, and artifact reproducibility improvements

Out of scope without prior discussion:

- unreviewed dependency sprawl
- hidden global state
- replacing the baseline scoring pipeline with unvalidated black-box models
- claiming physical solver results that are not produced by the codebase
