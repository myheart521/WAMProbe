# Contributing to WAMProbe

Thank you for helping make WAM evaluation more causal, reproducible, and control-grounded.

## Development setup

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
```

Before opening a pull request, run:

```bash
ruff format --check .
ruff check .
mypy
pytest --cov=wamprobe --cov-report=term-missing
```

## Contribution requirements

- Follow test-driven development for behavior changes.
- Keep the core package CPU-only and avoid heavy mandatory dependencies.
- New adapters must publish a capability declaration and pin an upstream revision used by
  their smoke test.
- New benchmarks must document generation, splits, licenses, and shared-state guarantees.
- New metrics must include a metric card, expected baseline ordering, and at least one
  failure/anti-gaming test.
- Do not commit datasets, checkpoints, generated runs, tokens, or browser sessions.

Please use focused commits and explain both the scientific reason and user-visible impact
of a change.
