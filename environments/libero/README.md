# LIBERO counterfactual pilot

This isolated runner generates four real action branches from one pinned LIBERO state. It
does not load StarWAM or any other model weights; it reuses the existing Python 3.11
environment because that environment already pins LIBERO, robosuite, MuJoCo, and Pillow.

```bash
environments/starwam/.venv/bin/python environments/libero/generate_cf_pilot.py \
  --gpu-index 0 --horizon 8
```

The default output is ignored by Git and written below `runs/libero-cf-pilot/`:

```text
benchmark_provenance.json
snapshots/integration_state.npy
snapshots/runtime_state.json
images/initial/*.png
images/<branch-id>/*.png
branches/<branch-id>.json
intervention_group.json
validation.json
```

The state file uses MuJoCo `mjSTATE_INTEGRATION`, which includes more integration state
than LIBERO's `time/qpos/qvel` wrapper snapshot. The JSON sidecar also records robosuite
clock state, controller state, Python and NumPy RNG state, and each gripper's stateful
`current_action`. Omitting `current_action` makes branch results depend on execution order
even when MuJoCo state restoration is exact.

The runner executes the branch set in forward and reverse order and repeats the no-op
branch. It fails after writing `validation.json` if restored state/observations, repeated
rollouts, or branch-order invariance are not exact.

The canonical initial observation is force-refreshed from the restored end-of-control
state. It is intentionally compared against a second independent restore, not against the
camera value returned by the preceding `step()`: robosuite can sample camera observables
inside the control interval before the final simulator state is reached.

## Verified fixed pilot

The pinned 4-branch × 8-step run was repeated twice on 2026-07-15 with identical hashes:

```text
snapshot semantic SHA256: 64560e918e964f8c772199dbc6b02e25f55ac7d8f2515649b69a4e25c1a9b53d
group SHA256:             cd7b68d5eb096b149a5ef927977455f7866ad76f4cabb38a8cd3f045d7e54654
artifact SHA256:          75552c33cc1dba35ed4a5dc1202db0de9f0ce74235fd85cee2b9c45ebd3c7648
maximum restore error:    0.0
```

Mean final end-effector pairwise distance was `0.0395948672` m, mean final raw
`object-state` pairwise distance was `0.0979067195`, and no-op end-effector drift was
`0.0000246710` m. Return spread and success rate were both zero. These diagnostic actions
validate paired branch generation and separation; they are not a task-solving policy or a
LIBERO success-rate result.
