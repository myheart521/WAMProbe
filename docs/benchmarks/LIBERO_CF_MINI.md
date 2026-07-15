# LIBERO-CF-Mini benchmark card

## Summary

LIBERO-CF-Mini v0.1 is WAMProbe's Tier-1 paired simulator benchmark. It starts several
candidate action sequences from an exactly restored simulator state and records their
state and RGB futures. The benchmark measures whether a model distinguishes action
consequences; it is not a LIBERO policy leaderboard and its diagnostic branches are not
expert actions.

The fixed task manifest covers four intentionally different families:

| Key | LIBERO suite | Family | Fixed task |
|---|---|---|---|
| `spatial-task0` | `libero_spatial` | spatial relation | black bowl between two objects → plate |
| `object-task0` | `libero_object` | object identity | alphabet soup → basket |
| `goal-task0` | `libero_goal` | articulated goal | open the middle drawer |
| `long-horizon-task0` | `libero_10` | long-horizon composition | two objects → basket |

The source selection, task text, BDDL/init-state filenames and hashes are pinned in
[`configs/benchmarks/libero_cf_mini_v0.1.json`](https://github.com/myheart521/WAMProbe/blob/main/configs/benchmarks/libero_cf_mini_v0.1.json).
The manifest's SHA256 is
`1660ab49ec0e5aac58f4801f0ec9a12326053f21f5f1974dd3b6ea63260f78c3`.

## Upstream data and license

- Source: [LIBERO](https://github.com/Lifelong-Robot-Learning/LIBERO)
- Revision: `8f1084e3132a39270c3a13ebe37270a43ece2a01`
- Upstream code, BDDL assets and fixed init states: MIT license
- WAMProbe-generated metadata: Apache-2.0
- No LIBERO demonstrations are required or redistributed by this benchmark slice.

Users redistributing generated image/state bundles should retain both projects' license
and provenance notices. The runner rejects an upstream commit, task description, BDDL,
init-state file, shape or dtype that differs from the manifest.

## Intervention protocol

Each task uses init state 0, 30 no-op settling steps, two 256×256 RGB cameras and an
eight-step branch horizon. Four constant commands are applied from one shared snapshot:

1. open-gripper no-op;
2. positive end-effector X;
3. negative end-effector X;
4. stationary gripper close.

The snapshot contains MuJoCo `mjSTATE_INTEGRATION` plus robosuite clock, controller,
observable, gripper and Python/NumPy RNG side state. Every task is checked with two
independent restores, a repeated no-op branch, and forward/reverse branch execution.
All state and image references carry size and SHA256 metadata.

## Verified v0.1 pilot

The four-task, 16-branch, 128-post-action-frame run completed on 2026-07-15. Every exact
restore check passed and the maximum integration-state error was `0.0`.

| Task | Snapshot SHA256 | Artifact SHA256 | EEF separation | Object-state separation | No-op drift |
|---|---|---|---:|---:|---:|
| spatial | `22f220ce…e36` | `73014e3d…ae97` | 0.0395949 | 0.0979067 | 0.0000247 |
| object | `d73e2f59…d8d3` | `2bfda04f…db1` | 0.0395781 | 0.1135034 | 0.0000762 |
| goal | `aadc9f6f…bef9` | `9e34e5df…bac3` | 0.0395915 | 0.0873014 | 0.0000340 |
| long-horizon | `ae5737d2…a082` | `014aea0c…df3a` | 0.0396259 | 0.1234343 | 0.0000605 |

Full hashes and values are available in
[`libero_cf_mini_verified_v0.1.json`](libero_cf_mini_verified_v0.1.json). A second run
verified the artifact JSON, snapshot sidecars and every PNG by size and SHA256, then
reported four cache hits without opening a simulator.

## Reproduction

Follow the isolated environment instructions in
[`environments/libero/README.md`](https://github.com/myheart521/WAMProbe/blob/main/environments/libero/README.md), then run:

```bash
environments/starwam/.venv/bin/python environments/libero/generate_cf_pilot.py \
  --gpu-index 0 --horizon 8 --run-dir runs/libero-cf-mini-v0.1
```

The command processes all four tasks by default and writes a structured failure record
to `index.json` after every task. Repeat `--task-key` to reproduce a smaller subset.
Valid existing artifacts resume as cache hits; use `--force` only to regenerate them.

## Suitable and unsuitable uses

Suitable uses include snapshot/restore validation, action-condition diagnostics, short
horizon state/video comparisons and model-integration smoke tests. Unsuitable uses
include reporting LIBERO task success, comparing policies, claiming task completion, or
aggregating raw object-state distances across tasks whose state vector dimensions differ.

## Limitations

- The four fixed commands are causal probes, not constraint-aware expert trajectories.
- Eight steps are too short for the selected sparse-reward tasks; all verified return
  spreads and success rates are zero. This is reported as a limitation, not hidden.
- The current branch set probes X translation and gripper closure only.
- One init state per family is insufficient for paper-level statistical claims.
- RGB similarity, keypoint metrics, real-WAM predictions and closed-loop control utility
  are separate evaluation stages and are not established by this data-generation run.
