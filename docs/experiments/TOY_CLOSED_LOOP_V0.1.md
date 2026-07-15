# Toy closed-loop utility study v0.1

## Question

Does a future scorer with better offline candidate ranking also obtain better return when
the selected action is actually executed and the scorer must replan from the resulting
state?

This study is an evaluator validation on exact analytic dynamics. It is not evidence that
the released StarWAM checkpoint improves closed-loop LIBERO performance: that adapter does
not expose action-conditioned candidate futures, so WAMProbe does not fabricate them.

## Fixed protocol

- benchmarks: BlockPush-2D v0.1 and Gripper-Catch v0.1;
- shared contexts: 12 per benchmark, suite seed 7;
- legal candidate set: the benchmark's full fixed candidate set at every cycle;
- prediction horizon: 6 steps for BlockPush, 5 for Gripper-Catch;
- episode budget: one benchmark horizon;
- execute prefix: one true-dynamics step before observing and replanning;
- score horizon: prediction prefix capped by remaining episode steps;
- ties: stable benchmark candidate order;
- uncertainty: 1,000 context-block bootstrap resamples;
- success: match the greedy simulator-future scorer's final return within `1e-9`.

Controllers include oracle, seeded noisy, copy-last, wrong-direction and action-agnostic
future scorers, plus a simulator-future scorer, a fixed action-only policy and deterministic
random selection. Offline CRC and Top-1 Regret are intentionally `null` for controllers
that do not emit candidate futures.

## Reproduce

```bash
wamprobe closed-loop-study \
  --benchmark all \
  --contexts 12 \
  --seed 7 \
  --execute-prefix 1 \
  --resamples 1000 \
  --output runs/closed-loop-study-v0.1
```

The canonical JSON SHA256 is
`19d2a0108fc19580da4e81f15226a4706a40c9d2c0513857d6bc8dc9000189b3`.

## Results

| Benchmark | Future scorer | Offline CRC | Offline regret | Closed return | Success |
|---|---|---:|---:|---:|---:|
| BlockPush | oracle | 1.0000 | 0.0000 | 0.0000 | 1.0000 |
| BlockPush | noisy | 1.0000 | 0.0000 | 0.0000 | 1.0000 |
| BlockPush | copy-last | 0.0000 | 0.3000 | -0.3000 | 0.0000 |
| BlockPush | wrong-direction | -0.2500 | 0.3000 | -0.3000 | 0.0000 |
| BlockPush | action-agnostic | 0.0000 | 0.3000 | -0.3000 | 0.0000 |
| Gripper-Catch | oracle | 1.0000 | 0.0000 | 1.0000 | 1.0000 |
| Gripper-Catch | noisy | 1.0000 | 0.0000 | 0.9967 | 0.9167 |
| Gripper-Catch | copy-last | 0.0000 | 1.0000 | 0.0000 | 0.0000 |
| Gripper-Catch | wrong-direction | 0.0000 | 1.0000 | 0.0000 | 0.0000 |
| Gripper-Catch | action-agnostic | 0.0000 | 1.0000 | 0.0000 | 0.0000 |

Across the five future-scorer profiles, offline CRC versus mean closed-loop return has
Pearson correlation `0.9855` for BlockPush and `1.0000` for Gripper-Catch. Offline Top-1
Regret versus return is `-1.0000` for both. No comparable future-scorer pair reverses the
offline-CRC/return ordering.

## Interpretation and limits

The result confirms that the evaluator connects offline action ranking to actual repeated
execution on two controlled tasks. It does not establish a population-level correlation:
there are only five deliberately separated reference profiles, three weak profiles tie on
return, and the contexts come from analytic generators rather than independent robot task
distributions. The action-only fixed policy also reaches the task optimum, showing that a
world model is not necessary on these easy generated tasks.

The first implementation used the full prediction endpoint even when fewer episode steps
remained. That made an exact model overrun the goal near termination. The released protocol
caps the scoring prefix by the remaining budget, and regression tests preserve this MPC
semantics. Larger LIBERO studies must likewise declare prediction horizon, execution prefix,
reward horizon, terminal handling and candidate generator before comparing controllers.
