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

The output directory contains `summary.json`, `report.md`, and a standalone
`report.html`. The JSON preserves per-context values, descriptive statistics,
context-block bootstrap intervals, and paired model differences.

## Built-in baselines

| Baseline | Behavior | Diagnostic purpose |
|---|---|---|
| `oracle-pointmass` | Uses exact dynamics | Expected upper bound |
| `noisy-linear` | Applies the action plus seeded transition noise | Checks smooth accuracy degradation |
| `copy-last-frame` | Predicts no movement | Detects action ignorance |
| `wrong-direction` | Applies the negative action | Separates dependence from correctness |
| `action-agnostic` | Moves to the goal for every action | Mimics a plausible success prior |

## Metrics

- **Action Dependence** measures endpoint separation across action branches. It does not
  establish that the direction is correct.
- **Permutation Effect** correlates true and predicted endpoint-distance geometry, then
  standardizes it against action-label permutations within the same context. Its p-value
  is reported separately; neither value replaces direction or dynamics metrics.
- **Counterfactual Direction Accuracy** is mean cosine alignment between predicted and
  true non-noop displacement. `1` is aligned, `0` is uninformative, and `-1` is reversed.
- **No-op Stability** is the fraction of no-op predictions whose final state remains at
  the shared initial position.
- **State ADE** is average Euclidean state error over branches and time; lower is better.
- **State FDE** is final-state Euclidean error averaged over every branch, including the
  no-op branch; lower is better.
- **Top-1 Regret** measures how much true return is lost by selecting the candidate that
  looks best under the predicted future; lower is better.

WAMProbe intentionally reports a metric profile, not a composite score. A model may be
action-dependent but physically wrong, or visually accurate but useless for candidate
selection.

Uncertainty is computed at the context level. Each bootstrap draw resamples whole shared
initial states, never individual action branches or adjacent frames. Paired comparisons
align exact context IDs and report the left-minus-right difference with a 95% interval.

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

## Run the opt-in StarWAM smoke probe

After reproducing the isolated environment in
[`environments/starwam/README.md`](../environments/starwam/README.md), select a physical
GPU with enough free memory and run the text encoder and action model in separate
processes:

```bash
environments/starwam/.venv/bin/python environments/starwam/run_libero_smoke.py \
  --mode text-cache --gpu-index 0 --minimum-free-gib 13

environments/starwam/.venv/bin/python environments/starwam/run_libero_smoke.py \
  --mode infer --gpu-index 0 --minimum-free-gib 15 \
  --num-inference-steps 1 --vae-device cpu
```

The runner fixes LIBERO suite/task/init state/wait steps and seed, verifies upstream
revisions and input hashes, records both camera transformations and proprio ordering, and
writes a cache-keyed prediction JSON below `runs/starwam-libero-smoke/`. Use the one-step
setting only as an integration smoke test; the published StarWAM recipe uses eight steps.

## Generate the paired LIBERO counterfactual pilot

This step uses the same isolated simulator environment but loads no model weights:

```bash
environments/starwam/.venv/bin/python environments/libero/generate_cf_pilot.py \
  --gpu-index 0 --horizon 8
```

The runner restores one fixed snapshot before `no-op`, positive/negative end-effector X,
and gripper-close branches. It stores two camera views and state descriptors for all eight
future steps, repeats no-op, and executes all branches in reverse order. A successful run
requires byte-identical MuJoCo integration states, force-refreshed initial observations,
repeated rollouts, and order-independent branch results. See
[`environments/libero/README.md`](../environments/libero/README.md) for the output layout
and the required Python-side gripper-state restoration.

## What this demo does not prove

PointMass-2D validates the evaluator and guards against metric bugs. The current LIBERO
pilot validates paired data generation for one context, not policy quality: its diagnostic
actions do not solve the task. Transfer claims still require multiple manipulation tasks,
WAM future predictions, stochastic generation analysis, and correlation with closed-loop
return.
