# StarWAM × LIBERO-CF-Mini v0.1 experiment

## Result

The fixed 2026-07-15 run completed 36/36 predictions and 36/36 simulator executions with
no failed samples or failed tasks. Four prediction executions were repeated from their
snapshots and matched exactly. Re-running inference produced 36/36 verified cache hits.

Configuration:

- model: `starwam-wan22-5b-mot-libero`;
- tasks: spatial, object, articulated-goal and long-horizon composition;
- diffusion seeds: 0, 1, 2;
- action NFE: 1, 4, 8;
- output action shape: 32 × 7;
- executed prefix horizons: 8, 16, 32.

## Efficiency

| NFE | Samples | Mean latency | Peak allocated | Action RMS | Mean step change |
|---:|---:|---:|---:|---:|---:|
| 1 | 12 | 0.7798 s | 11.388 GiB | 0.4594 | 0.0638 |
| 4 | 12 | 0.9722 s | 11.388 GiB | 0.4604 | 0.0519 |
| 8 | 12 | 1.2160 s | 11.388 GiB | 0.4615 | 0.0514 |

NFE and latency had Pearson correlation 0.8668 in this small repeated matrix. Increasing
NFE cost more latency but did not yield any sparse success.

## Simulator outcomes

| Prefix | Executions | Success | Mean return | Mean EEF displacement |
|---:|---:|---:|---:|---:|
| 8 | 36 | 0.0000 | 0.0000 | 0.1716 m |
| 16 | 36 | 0.0000 | 0.0000 | 0.1121 m |
| 32 | 36 | 0.0000 | 0.0000 | 0.0000 m |

The 32-step chunks returned the EEF to its task-specific initial position even though
simulator and object state changed. Longer open-loop execution therefore did not
monotonically increase control displacement or utility. This supports reporting horizon
profiles rather than assuming the largest action chunk is best.

Mean action RMS differences were 0.009067 across seeds and 0.011779 across NFE settings.
Mean executed EEF differences across NFE were 0.001790/0.003121/0.004164 m at horizons
8/16/32; across seeds they were 0.000798/0.001142/0.001882 m.

## Explicit skips and negative results

- Candidate-action mask/shuffle: skipped because the verified adapter has no candidate
  action input or action-conditioned future endpoint.
- Predicted-video quality versus control: skipped because the adapter returns no future
  video/state artifact; inventing PSNR/SSIM/FVD would be invalid.
- Success correlation: undefined because sparse success and return are constant zero.
- The zero-success outcome is retained. It is a fixed-context, short open-loop diagnostic,
  not a claim that the upstream policy has zero LIBERO benchmark success.

## Reproduction and hashes

```bash
environments/starwam/.venv/bin/python environments/starwam/run_libero_smoke.py \
  --mode matrix --gpu-index 0 --minimum-free-gib 18 --vae-device cpu \
  --run-dir runs/starwam-libero-cf-mini-v0.1

environments/starwam/.venv/bin/python \
  environments/starwam/execute_prediction_matrix.py \
  --gpu-index 0 --matrix-dir runs/starwam-libero-cf-mini-v0.1

wamprobe experiment-report \
  runs/starwam-libero-cf-mini-v0.1/matrix-index.json \
  runs/starwam-libero-cf-mini-v0.1/execution-index.json \
  --output runs/starwam-libero-cf-mini-v0.1/report
```

Verified evidence identities:

- matrix index SHA256: `61fd988ea648922652ef2ab23f08b14a9849d37353d2e4894eb839fe3dfdb12d`;
- execution index SHA256: `3bb9d5bdab9437cf07b0ed6567a8ddb146191447931a59a098b853e2fd3e9846`;
- LIBERO-CF manifest SHA256: `1660ab49ec0e5aac58f4801f0ec9a12326053f21f5f1974dd3b6ea63260f78c3`.

The indexes and raw predictions remain ignored locally until a user-approved release
bundle is published. Each prediction artifact carries its own input cache key and output
SHA256; the committed report records the aggregate evidence without committing weights,
RGB frames or simulator states.
