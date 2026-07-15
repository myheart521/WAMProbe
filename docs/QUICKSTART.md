# Quick start and metric interpretation

## Run the diagnostic suite

From a source checkout:

```bash
PYTHONPATH=src python -m wamprobe demo \
  --contexts 12 \
  --seed 7 \
  --output runs/pointmass-demo
```

The suite creates multiple actions from each shared initial state. The goal is placed at
the final state of one directional action, so the simulator's optimal candidate is known
exactly.

## Built-in baselines

| Baseline | Behavior | Diagnostic purpose |
|---|---|---|
| `oracle-pointmass` | Uses exact dynamics | Expected upper bound |
| `copy-last-frame` | Predicts no movement | Detects action ignorance |
| `wrong-direction` | Applies the negative action | Separates dependence from correctness |
| `action-agnostic` | Moves to the goal for every action | Mimics a plausible success prior |

## Metrics

- **Action Dependence** measures endpoint separation across action branches. It does not
  establish that the direction is correct.
- **Counterfactual Direction Accuracy** is mean cosine alignment between predicted and
  true non-noop displacement. `1` is aligned, `0` is uninformative, and `-1` is reversed.
- **No-op Stability** is the fraction of no-op predictions whose final state remains at
  the shared initial position.
- **State ADE** is average Euclidean state error over branches and time; lower is better.
- **Top-1 Regret** measures how much true return is lost by selecting the candidate that
  looks best under the predicted future; lower is better.

WAMProbe intentionally reports a metric profile, not a composite score. A model may be
action-dependent but physically wrong, or visually accurate but useless for candidate
selection.

## Validate real-model artifacts

The first real adapter uses pinned StarWAM and Wan2.2 files stored outside Git. Follow
[`checkpoints/README.md`](../checkpoints/README.md), then run:

```bash
wamprobe doctor
wamprobe doctor --verify-hashes
```

Exit code `0` means every required model passed. Exit code `1` means an artifact is
missing, incomplete, the wrong size/hash, or from a conflicting recorded revision. Exit
code `2` means the manifest itself could not be read safely. Use `--json` for automation.

## What this demo does not prove

PointMass-2D validates the evaluator and guards against metric bugs. It is not evidence
that the metrics transfer to manipulation videos. That requires paired simulator branches,
perception-based state extraction, stochastic generation analysis, and correlation with
closed-loop return; these are explicit later milestones.
