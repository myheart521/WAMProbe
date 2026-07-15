# RFC 0001: Scope and capability-aware adapters

- Status: Accepted for alpha
- Version: 0.1

## Decision

WAMProbe treats World Action Models as a family rather than one architecture. An adapter
declares the future representation it exposes (`none`, `pixels`, `states`, or `latents`)
and whether it predicts actions, scores candidate actions, exposes world features, supports
batching, or provides deterministic seeding.

Metrics must state the capabilities they require. Missing capabilities are skipped with an
explicit reason or rejected before evaluation; they are never silently approximated.

## Alpha protocol

The CPU-first alpha requires one method:

```python
predict_future(context, action, *, horizon, seed) -> Trajectory2D
```

This narrow state-space contract establishes ID alignment, horizon validation, intervention
semantics, and deterministic tests. Pixel/latent batches and remote dependency isolation are
planned extensions that will preserve the same capability-routing principle.

## Non-goals

- defining a universal robot action space in this repository;
- forcing auxiliary-video WAMs to expose pixel rollouts;
- treating unsupported metrics as zero;
- ranking heterogeneous capability groups with one aggregate score.
