# StarWAM adapter model card

The machine-readable capability declaration is pinned in
[`configs/models/starwam-capabilities-v0.1.json`](https://github.com/myheart521/WAMProbe/blob/main/configs/models/starwam-capabilities-v0.1.json)
and validated against the public Draft 2020-12 capability schema in CI.

## Model and adapter identity

| Field | Value |
|---|---|
| WAMProbe model ID | `starwam-wan22-5b-mot-libero` |
| Upstream code | `shaohua-pan/StarWAM@f6c771fc3be0a9bc271ea4f1531d8ea35efb0ec7` |
| Released model | `panshaohua/starwam@7d4bfe3ec76172ca17169fa959d21da099d386fe` |
| Checkpoint SHA256 | `d24edea01579880327cfd9dc84d24adab82e420dca9652e614ad697bc8cc5378` |
| Backbone | Wan2.2 TI2V-5B revision `921dbaf3f1674a56f47e83fb80a34bac8a8f203e` |
| Adapter version | `0.1.0` |
| Upstream code/model license | Apache-2.0 as declared by upstream repositories |

The WAMProbe adapter is an isolated integration target, not a reimplementation or an
endorsement by the StarWAM authors. Weights remain outside Git.

## Verified interface

Input:

- two ordered 256×256 RGB cameras (`agentview`, `wrist`), rotated 180° and resized to
  224×224 before horizontal concatenation;
- eight proprioceptive values: EEF position, axis-angle orientation and two gripper
  positions;
- the LIBERO natural-language task, encoded with the pinned UMT5-XXL text encoder;
- an explicit non-negative diffusion seed.

Output:

- 32 × 7 denormalized LIBERO delta-pose/gripper action chunk;
- measured latency, device, dtype and peak allocated/reserved GPU memory;
- full code/model/preprocessing/inference provenance and a prediction payload SHA256.

## Declared capabilities

The released integration is verified for observation/task → action prediction. It does
not expose an action-conditioned `predict_future(candidate_action)` endpoint, future RGB
video, future state, uncertainty or likelihood through the WAMProbe adapter. Therefore:

- StarWAM action chunks can be executed and scored in LIBERO;
- NFE, seed and executed-prefix horizon can be evaluated;
- candidate-action mask/shuffle, PSNR/SSIM/FVD and future-state ADE/FDE are skipped with
  structured reasons for this adapter;
- internal video/world features are not relabeled as predicted videos.

## Verified evaluation

The 2026-07-15 matrix used four LIBERO-CF-Mini task families, seeds 0/1/2 and NFE
1/4/8: 36 predictions and 36 action executions completed with zero runtime failures. A
second inference pass returned 36 SHA-verified cache hits. Mean latency rose from 0.780 s
at NFE 1 to 1.216 s at NFE 8 while peak allocation remained about 11.39 GiB.

Actions were executed from the same content-addressed snapshots with checkpoints after
8/16/32 controls. Sparse success and return were zero for every fixed context. Mean EEF
displacement was 0.1716/0.1121/0.0000 m, showing that a longer open-loop action prefix did
not monotonically improve control. This is a negative short-horizon diagnostic result,
not a LIBERO policy success-rate estimate.

See the [experiment report](../experiments/STARWAM_LIBERO_CF_MINI_V0.1.md) and
[LIBERO-CF-Mini benchmark card](../benchmarks/LIBERO_CF_MINI.md).

## Limitations and risks

- Four fixed init states cannot estimate general LIBERO success.
- The checkpoint was evaluated without retraining or calibration.
- Open-loop prefixes can leave the training distribution; WAMProbe does not assert robot
  safety or constraint satisfaction.
- Seed/NFE sensitivity is descriptive with only three values per axis.
- The current adapter cannot isolate whether internal future features caused an action.
- Results depend on pinned CUDA/PyTorch/MuJoCo hardware and software; GPU nightly evidence
  should be treated as a reproducibility check, not numerical bit-equivalence across GPUs.
