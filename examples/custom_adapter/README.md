# Custom adapter starter kit

This runnable example shows the smallest safe bridge between a custom
state-future model and WAMProbe. The adapter preserves the context ID and action
name, passes an explicit action intervention to the backend, validates the
prediction horizon and finite coordinates, and declares machine-readable model
capabilities.

Run it from the repository root:

```bash
python -m examples.custom_adapter.run \
  --output runs/custom-adapter \
  --contexts 8 \
  --seed 0
```

The command writes `summary.json`, `results.jsonl`, `report.md`, and
`report.html`. The included linear backend should achieve zero Top-1 Regret on
PointMass2D; this is a wiring check, not a research result.

To connect a model:

1. Implement `StateFutureBackend.predict_positions()` in `adapter.py`.
2. Map every field in `PredictionRequest` to your model input without dropping
   the action intervention or context identity.
3. Return exactly one `(x, y)` state per requested horizon step.
4. Update `ModelCapabilities` if your backend is stochastic or has different
   behavior.
5. Run this example, then add model-specific tests before submitting results.

See [`docs/adapters/CUSTOM_ADAPTER.md`](../../docs/adapters/CUSTOM_ADAPTER.md)
for the full integration and submission guide.
