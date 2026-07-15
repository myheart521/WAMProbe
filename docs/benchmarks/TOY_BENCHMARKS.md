# WAMProbe analytic toy benchmarks

The toy tier exists to test evaluator behavior against dynamics whose failure modes are
known exactly. It is not a manipulation-success benchmark and should not be used to make
claims about photorealism or real-robot transfer.

## Shared contract

`BlockPush2D` and `GripperCatch` expose the same dependency-free contract:

- one shared initial `ManipulationState` per context;
- two or more typed `ManipulationAction` branches;
- an exact state transition and an optional seeded noisy transition;
- a simulator-return function and an analytic optimal candidate;
- a 64×64 tightly packed RGB observation plus named proprioceptive fields.

The metric state vector is:

```text
[effector_x, effector_y, object_x, object_y,
 gripper_closed, object_attached, in_contact]
```

Boolean contact semantics remain explicit instead of being inferred from action names.
Noise streams are content-addressed by the run seed, context ID, and action name, so
reordering contexts or branches does not change a prediction.

## BlockPush-2D v0.1

The pusher begins three action steps behind the block. The first step is necessarily a
pre-contact approach. Once the pusher is within the contact reach and moving toward the
block, the block follows its planar transition. Perpendicular and away-from-object
commands cannot move the block under deterministic dynamics.

Candidate actions are no-op and pushes in four cardinal directions. The generated goal
is reached by exactly one direction after the approach phase. Return is negative final
block-to-goal distance.

This model deliberately omits mass, friction, rotation, and rigid-body collision
resolution. Those belong in the LIBERO tier; here, the two-stage contact causal boundary
is the behavior under test.

## Gripper-Catch v0.1

An object falls by a fixed vertical displacement while the gripper chooses open no-op,
closed-left, closed-stationary, or closed-right motion. Attachment requires both spatial
alignment and an explicit close command. Once attached, the object follows the gripper
and an attached state with an open gripper is rejected by the data model.

The three generated context families place the falling object at the endpoint of the
left, stationary, or right closed candidate. Return rewards a valid attachment and then
penalizes final object-to-goal distance.

This is a semantic grasp diagnostic, not a model of finger geometry, impact, bounce, or
force closure.

## Run

```bash
wamprobe demo --benchmark pointmass --contexts 12 --seed 7
wamprobe demo --benchmark blockpush --contexts 12 --seed 7 --horizon 6 \
  --output runs/blockpush-demo
wamprobe demo --benchmark gripper-catch --contexts 12 --seed 7 --horizon 5 \
  --output runs/gripper-catch-demo
```

Each command writes versioned JSON, Markdown, and standalone HTML. CRC reports Spearman,
Kendall tau-b, NDCG over shifted non-negative relevance, and pairwise preference
accuracy. Tied model predictions receive half credit in pairwise accuracy; ground-truth
ties are excluded from that denominator.

The suite generator accepts `contexts=1000` without external assets or simulator
installation. Generated suites are deterministic for a fixed benchmark configuration and
seed and can be exported as checksummed intervention JSONL.

## Closed-loop protocol

`wamprobe closed-loop-study` turns BlockPush and Gripper-Catch into a Tier-2 evaluator.
At each cycle it scores the unchanged legal candidate set, executes only the selected
trajectory prefix under exact benchmark dynamics, creates a new context from the resulting
state, and scores again. The default prefix is one step and the default episode budget is
the benchmark horizon (six BlockPush steps or five Gripper-Catch steps). Candidate scoring
uses `min(prediction_horizon, remaining_episode_steps)`; this avoids rewarding or
penalizing terminal predictions beyond the actual execution budget.

The fixed comparison set contains five future-prediction adapters, deterministic random
selection, an initial-context fixed action policy, and a greedy simulator-future scorer.
Success means matching the simulator scorer's final return within `1e-9` for these exact
analytic tasks. This equality is an evaluator sanity definition and must not be reused as a
general robot-task success threshold. Full settings, results, and limitations are in the
[experiment card](../experiments/TOY_CLOSED_LOOP_V0.1.md).
