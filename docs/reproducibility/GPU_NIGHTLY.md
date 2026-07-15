# GPU nightly runner guide

The GPU workflow is intentionally disabled until a trusted self-hosted runner is
provisioned. Set repository variable `WAMPROBE_GPU_NIGHTLY_ENABLED=true` only after the
runner has labels `self-hosted`, `linux`, `x64`, `gpu` and the following ignored assets:

- `environments/starwam/.venv/` with the pinned Python 3.11 environment;
- `vendor/upstream/starwam` and `vendor/upstream/libero` at documented commits;
- `checkpoints/upstream/` matching `wamprobe doctor`.

Checkout uses `clean: false` so Git does not delete these provisioned ignored assets. Do
not attach the runner to untrusted pull-request workflows. The scheduled job reads only
the default branch, has `contents: read`, times out after 90 minutes and uploads structured
indexes/reports for 14 days. The default nightly is one task/seed/NFE; manual dispatch can
select the complete 36-prediction matrix.

Before enabling the schedule, run locally:

```bash
environments/starwam/.venv/bin/python -m wamprobe doctor --verify-hashes
environments/starwam/.venv/bin/python environments/starwam/run_libero_smoke.py \
  --mode matrix --task-key spatial-task0 --matrix-seed 0 \
  --matrix-inference-steps 1 --run-dir runs/gpu-nightly
```
