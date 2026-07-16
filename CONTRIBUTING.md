# Contributing to WAMProbe

Thank you for helping make WAM evaluation more causal, reproducible, and control-grounded.

## Choose a contribution path

- **Connect a model:** run the
  [custom adapter starter](docs/adapters/CUSTOM_ADAPTER.md), then open an
  [Adapter proposal](https://github.com/myheart521/WAMProbe/issues/new?template=adapter_proposal.yml).
- **Add a paired diagnostic:** open a
  [Benchmark proposal](https://github.com/myheart521/WAMProbe/issues/new?template=benchmark_proposal.yml)
  before generating a large dataset.
- **Add or change a metric:** open a
  [Metric proposal](https://github.com/myheart521/WAMProbe/issues/new?template=metric_proposal.yml)
  and state how the metric can be gamed.
- **Share a run:** use the
  [Experiment result](https://github.com/myheart521/WAMProbe/issues/new?template=experiment_result.yml)
  form with standard artifacts and hashes.
- **Share an optional independent reproduction:** use the
  [External reproduction](https://github.com/myheart521/WAMProbe/issues/new?template=external_reproduction.yml)
  form. A maintainer-controlled run must be labeled as maintainer evidence, never as an
  independent report.
- **Pick a bounded task:** see the
  [roadmap](docs/NEXT_STEPS.md) and issues labeled
  [`good first issue`](https://github.com/myheart521/WAMProbe/labels/good%20first%20issue).

## Development setup

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
```

Verify the adapter starter before replacing its backend:

```bash
python -m examples.custom_adapter.run \
  --output runs/custom-adapter \
  --contexts 8 \
  --seed 7
```

Before opening a pull request, run:

```bash
ruff format --check .
ruff check .
mypy
python scripts/validate_repository.py
mkdocs build --strict
pytest --cov=wamprobe --cov-report=term-missing --cov-fail-under=85
```

Changes to public schemas, committed evidence, package metadata, or release tooling must
also run `.venv/bin/python scripts/build_release_candidate.py` from a clean commit. Do not
use `--allow-dirty` as release evidence; that switch exists only for local development of
the audit itself.

## Contribution requirements

- Follow test-driven development for behavior changes.
- Keep the core package CPU-only and avoid heavy mandatory dependencies.
- New adapters must publish a capability declaration and pin an upstream revision used by
  their smoke test. Preserve context/action identities and reject malformed model outputs
  at the adapter boundary.
- New benchmarks must document generation, splits, licenses, and shared-state guarantees.
- New metrics must include a metric card, expected baseline ordering, and at least one
  failure/anti-gaming test.
- Do not commit datasets, checkpoints, generated runs, tokens, or browser sessions.
- Result submissions must identify the WAMProbe, adapter, model, checkpoint, preprocessing,
  and benchmark revisions; include exact commands and public artifact hashes.

Please use focused commits and explain both the scientific reason and user-visible impact
of a change.
