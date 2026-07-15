# WAMProbe

[![CI](https://github.com/myheart521/WAMProbe/actions/workflows/ci.yml/badge.svg)](https://github.com/myheart521/WAMProbe/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-green.svg)](LICENSE)

**Counterfactual evaluation for World Action Models.**

WAMProbe tests whether a World Action Model (WAM) predicts futures that are causally
controlled by the input action and useful for choosing robot actions. It complements
task-success and video-quality benchmarks with paired interventions:

```text
the same initial state
├── no-op       → predicted future / true future
├── move left   → predicted future / true future
├── move right  → predicted future / true future
└── expert act  → predicted future / true future
```

The project is in an early alpha. Its first runnable slice is deliberately small and
CPU-only: an analytic PointMass-2D benchmark verifies the public API and metrics against
an oracle and several intentionally broken baselines before expensive robot models are
integrated.

## Why another evaluation project?

A model can generate a realistic-looking success video while ignoring the candidate
action. WAMProbe separates three questions that should not be collapsed into one score:

1. **Action dependence:** do different actions produce different predicted futures?
2. **Direction correctness:** do those differences agree with true dynamics?
3. **Control utility:** does the predicted future select a better candidate action?

For example, the built-in `wrong-direction` baseline receives a high Action Dependence
score because it reacts to actions, but a negative Counterfactual Direction score because
it predicts the opposite motion. This sanity check prevents a superficially responsive
model from looking correct.

## Quick start

```bash
git clone https://github.com/myheart521/WAMProbe.git
cd WAMProbe
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .

wamprobe demo --contexts 12 --seed 7 --output runs/pointmass-demo
```

The command creates:

```text
runs/pointmass-demo/
├── summary.json  # versioned machine-readable results
└── report.md     # human-readable metric comparison
```

See the committed [example report](examples/pointmass-demo/report.md) for the expected
baseline ordering.

You can also run the module directly:

```bash
PYTHONPATH=src python -m wamprobe demo --output runs/pointmass-demo
```

## Current runnable scope

- typed, model-agnostic `WAMAdapter` protocol;
- capability manifest data model and JSON Schema;
- paired PointMass-2D counterfactual interventions;
- oracle, copy-last-frame, wrong-direction, and action-agnostic baselines;
- Action Dependence, Counterfactual Direction Accuracy, No-op Stability, state ADE,
  and Top-1 Regret;
- JSON and Markdown reports;
- Python 3.11–3.13 CI with linting, strict typing, and coverage.

## Roadmap

The next milestones are:

1. context-block bootstrap confidence intervals;
2. a small image-rendered BlockPush benchmark;
3. the versioned intervention dataset loader;
4. LIBERO-CF-Mini paired simulator branches;
5. a pinned StarWAM inference adapter, followed by LingBot-VA as a published reference.

See the [detailed Chinese project plan](docs/WAMProbe_PLAN.md),
[quick-start notes](docs/QUICKSTART.md), [failure-case evidence map](docs/research/WAM_VLA_FAILURE_CASES.md),
[adapter selection record](docs/research/ADAPTER_SELECTION.md), and [design RFCs](docs/rfcs/).

## Development

```bash
python -m pip install -e '.[dev]'
ruff format --check .
ruff check .
mypy
pytest --cov=wamprobe --cov-report=term-missing
```

Contributions are welcome. New metrics must include a documented failure mode and a
sanity test against the reference baselines; see [CONTRIBUTING.md](CONTRIBUTING.md).

## 中文说明

WAMProbe 不是新的 WAM 训练框架，而是一套“给 WAM 做反事实考试”的工具。它在完全
相同的初始状态下执行多个不同动作，比较模型预测未来与模拟器真实未来，并检查这些
预测是否能帮助机器人选出更好的动作。详细设计见
[WAMProbe 开源项目规划](docs/WAMProbe_PLAN.md)。
