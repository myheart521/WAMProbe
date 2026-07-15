# Quick start and metric interpretation

## Run the diagnostic suite

From a source checkout:

```bash
PYTHONPATH=src python -m wamprobe demo \
  --benchmark pointmass \
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

Run the contact and attachment variants through the same evaluator:

```bash
wamprobe demo --benchmark blockpush --contexts 12 --seed 7 --horizon 6 \
  --output runs/blockpush-demo
wamprobe demo --benchmark gripper-catch --contexts 12 --seed 7 --horizon 5 \
  --output runs/gripper-catch-demo
```

BlockPush has an explicit pre-contact approach followed by object motion only under a
directed contact. Gripper-Catch requires both alignment and a close command before the
falling object attaches. Both expose exact state and dependency-free 64×64 RGB
observations. See the [toy benchmark card](benchmarks/TOY_BENCHMARKS.md) for equations,
state fields, and limitations.

## Built-in baselines

| Baseline | Behavior | Diagnostic purpose |
|---|---|---|
| `oracle-pointmass` | Uses exact dynamics | Expected upper bound |
| `noisy-linear` | Applies the action plus seeded transition noise | Checks smooth accuracy degradation |
| `oracle-simulator` | Uses exact BlockPush/Gripper-Catch dynamics | Manipulation upper bound |
| `noisy-dynamics` | Adds content-addressed transition noise | Contact/grasp robustness check |
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
- **No-op Stability** checks a stationary no-op in PointMass. In a passive dynamic scene
  such as a falling object, the same field measures agreement with the true no-op future
  rather than incorrectly requiring the world to freeze.
- **State ADE** is average Euclidean state error over branches and time; lower is better.
- **State FDE** is final-state Euclidean error averaged over every branch, including the
  no-op branch; lower is better.
- **Top-1 Regret** measures how much true return is lost by selecting the candidate that
  looks best under the predicted future; lower is better.
- **Candidate Ranking Correlation (CRC)** compares all predicted candidate returns with
  simulator returns. WAMProbe reports Spearman, Kendall tau-b, NDCG, and pairwise
  preference accuracy rather than hiding their different tie behavior in one number.

WAMProbe intentionally reports a metric profile, not a composite score. A model may be
action-dependent but physically wrong, or visually accurate but useless for candidate
selection.

## Compare video fidelity with control value

Run the deterministic counterexample study on both rendered manipulation benchmarks:

```bash
wamprobe video-control-study \
  --benchmark all \
  --contexts 12 \
  --seed 7 \
  --output runs/video-control-study
```

The command writes `video-control-study.json` and `video-control-study.md`. It reports
PSNR and an explicitly labeled whole-frame global SSIM next to state FDE, Candidate
Ranking Correlation, and Top-1 Regret. The `appearance-corrupted-oracle` deliberately
inverts rendered RGB while preserving exact dynamics: it therefore has FDE `0`, CRC `1`,
and regret `0`, despite PSNR below `1 dB` in the committed run. This is a controlled metric
counterexample, not a claim that visual fidelity is unimportant. See the
[committed report](../examples/video-control-study/video-control-study.md).

## Run minimal closed-loop replanning

The closed-loop study uses the same candidate set at every decision, scores candidate
futures, executes only the first true-dynamics step, then rebuilds the context from the
resulting state and replans:

```bash
wamprobe closed-loop-study \
  --benchmark all \
  --contexts 12 \
  --seed 7 \
  --execute-prefix 1 \
  --resamples 1000 \
  --output runs/closed-loop-study
```

`--control-steps` overrides the default episode budget of one benchmark horizon.
`--execute-prefix` controls how many selected chunk steps are executed before observing
again. Candidate scores use at most the remaining episode budget, so a perfect fixed-
horizon predictor is not penalized by a terminal score beyond the steps that can be
executed.

The report compares five future scorers with a simulator-future scorer, a fixed action-only
policy, and deterministic random candidate selection. It preserves every context's chosen
action sequence, final return, success, and gap to the simulator scorer. The committed
12-context run found CRC/closed-return Pearson values of `0.9855` on BlockPush and `1.0000`
on Gripper-Catch, but these are descriptive associations across only five future-scorer
profiles. See the [report](../examples/closed-loop-study/closed-loop-study.md) and
[experiment card](experiments/TOY_CLOSED_LOOP_V0.1.md).

## Audit a release candidate

From a clean commit, the candidate command builds twice with the commit timestamp as
`SOURCE_DATE_EPOCH`, verifies identical wheel/sdist hashes and evidence identities, then
installs the wheel offline in a fresh environment and runs a two-context demo:

```bash
uv sync --extra dev --locked
.venv/bin/python scripts/build_release_candidate.py
```

The command writes ignored artifacts and `release-manifest.json` below
`dist/release-candidate/`. It does not publish or tag anything. See the
[release procedure](../release/README.md) and
[reproducibility guide](reproducibility/REPRODUCIBILITY.md).

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
  --gpu-index 0 --horizon 8 --run-dir runs/libero-cf-mini-v0.1
```

The runner restores one fixed snapshot in each of four task families before `no-op`,
positive/negative end-effector X, and gripper-close branches. It stores two camera views
and state descriptors for all eight
future steps, repeats no-op, and executes all branches in reverse order. A successful run
requires byte-identical MuJoCo integration states, force-refreshed initial observations,
repeated rollouts, and order-independent branch results. See
[`environments/libero/README.md`](../environments/libero/README.md) for the output layout
and the required Python-side gripper-state restoration. Repeat `--task-key` to select a
subset; verified outputs resume without reopening the simulator.

## What this demo does not prove

PointMass-2D validates the evaluator and guards against metric bugs. The current LIBERO
pilot validates paired data generation across four task families, not policy quality: its
diagnostic actions do not solve the tasks. Transfer claims still require more initial
states, action-conditioned real-WAM future predictions, stochastic generation analysis,
and real-model closed-loop return. The analytic closed-loop study validates evaluator
behavior; it does not fill those transfer gaps.
