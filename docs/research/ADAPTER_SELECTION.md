# First real WAM adapter selection

- Decision date: 2026-07-15
- Status: implementation preflight passed
- Target: first GPU-backed adapter after the CPU PointMass vertical slice

## Decision

Use **StarWAM** as the first implementation target, pinned to code commit
`f6c771fc3be0a9bc271ea4f1531d8ea35efb0ec7` and ModelScope model revision
`7d4bfe3ec76172ca17169fa959d21da099d386fe`.

Use **LingBot-VA** as the second, published-reference adapter. Keep **Fast-WAM** as an
action-only/feature-conditioned comparison after its checkpoint license metadata is made
explicit.

This decision selects an integration target; it does not claim that StarWAM is the best
policy. The first milestone is a reproducible inference probe, not training or leaderboard
comparison.

## Hard gates

An adapter is eligible only when all of the following can be checked:

1. code license and model-weight terms are identifiable;
2. a public checkpoint is downloadable at a pin-able revision;
3. inference exposes actions, futures, or world features that can be declared honestly;
4. a supported benchmark and action normalization path exist;
5. Python, PyTorch, CUDA, and simulator dependencies can be isolated;
6. evaluation fits the available hardware or documents a concrete offload path.

## Candidate audit

| Candidate | Code / weights | Observable capability | Reproducibility and compute | Decision |
|---|---|---|---|---|
| StarWAM | Apache-2.0 / ModelScope reports Apache-2.0 | MoT, Shared-DiT, and feature-conditioned families; video/world and action paths; LIBERO recipes | Python 3.11 recipe, PyTorch 2.6/CUDA 12.4, single-GPU rollout command, released 5B checkpoints; training launchers default to 8 GPUs | **First target** |
| LingBot-VA | Apache-2.0 / Hugging Face model card tags Apache-2.0 | autoregressive video-action generation, action inference, LIBERO and RoboTwin evaluation | Python 3.10.16, PyTorch 2.9/CUDA 12.6; README reports about 18 GB VRAM for image-to-video-action and 24 GB for RoboTwin with offload | **Second reference** |
| Fast-WAM | MIT / public checkpoint has no explicit license tag in the Hugging Face API | direct action output at inference; video co-training features, but no decoded future in the primary inference path | Python 3.10, PyTorch 2.7.1/CUDA 12.8; benchmark manager defaults to 8 GPUs and can be reduced | **Defer full integration** |

## Why StarWAM first

- Its taxonomy-level model families map directly onto WAMProbe's capability protocol.
- The same codebase can exercise `future_pixels`, `world_features`, and action-oriented
  variants without pretending they support identical metrics.
- It includes LIBERO recipes, rollout utilities, action statistics, and two released
  checkpoint families.
- Its code and weight repository both identify Apache-2.0 terms.
- The local host has four RTX 4090 GPUs with 24 GB VRAM each, which makes a focused
  inference spike plausible without committing to retraining.

## Risks and controls

| Risk | Control |
|---|---|
| StarWAM is an early research release without a technical report | Treat it as an API/protocol integration target; use LingBot-VA for paper-backed comparison |
| ModelScope model card is a default template | Pin the Git revision and checksum every downloaded file before inference |
| The model repository is roughly 32.1 GB before the separate backbone | Start with one checkpoint family and document disk/VRAM measurements |
| Training recipes use eight GPUs | Do not train in the first adapter milestone; validate one-context inference and cached outputs |
| Action and state normalization may silently mismatch | Store upstream stats hash and normalization metadata in every WAMProbe result |
| Pixel and feature variants expose different evidence | Declare capabilities explicitly; skip incompatible metrics with a reason |

## Pinned upstream snapshot

| Item | Pin or observation |
|---|---|
| StarWAM code | [`shaohua-pan/StarWAM@f6c771f`](https://github.com/shaohua-pan/StarWAM/tree/f6c771fc3be0a9bc271ea4f1531d8ea35efb0ec7) |
| StarWAM weights | [`panshaohua/starwam@7d4bfe3`](https://www.modelscope.cn/models/panshaohua/starwam) |
| LingBot-VA code | [`Robbyant/lingbot-va@7c6ffa9`](https://github.com/Robbyant/lingbot-va/tree/7c6ffa9bfc4b83582cafc860fab4c82cc7deeeeb) |
| LingBot-VA LIBERO weights | Hugging Face revision `0e89d1e753019988aba484e8da2dc0810e264d9f` |
| Fast-WAM code | [`yuantianyuan01/FastWAM@45d8e14`](https://github.com/yuantianyuan01/FastWAM/tree/45d8e1458921d83f8ad6cf9ce993d371208dabd0) |
| Fast-WAM weights | Hugging Face revision `139eebb6d90cdd9bdbbe465f72c6edc9ad5a518a`; weight license metadata unresolved |

Pins record what was audited. They should be updated only through a reviewed compatibility
change, not silently moved to an upstream default branch.

## Implementation preflight result

The pinned Wan2.2 and StarWAM artifacts were downloaded and verified on 2026-07-15. The
required files total 46.25 GB, both model groups pass `wamprobe doctor --verify-hashes`,
and no incomplete fragments remain. An isolated Python 3.11 / PyTorch 2.6.0+cu124
environment imports the pinned StarWAM source successfully.

Restricted checkpoint inspection found only tensor mappings in the StarWAM, Wan VAE, and
Wan T5 payloads. A meta-device architecture build matched all 3,300 checkpoint keys with
zero missing or unexpected entries. A load-only test on one RTX 4090 peaked at 12.16 GB
allocated and 12.38 GB reserved, used deterministic seed 42 and evaluation mode, and
released the allocation afterward.

These results clear artifact, environment, architecture, and loadability gates only. No
LIBERO observation was executed, so action correctness, preprocessing correctness, runtime
latency, and rollout success remain unverified.

## First adapter implementation slice

The next coding slice is deliberately narrow:

1. add a `starwam` optional dependency group or isolated environment specification;
2. implement metadata-only discovery and `wamprobe doctor` compatibility checks first;
3. download one checkpoint family and record immutable hashes outside Git;
4. run one LIBERO observation through upstream inference and save a typed, cached artifact;
5. expose only capabilities verified from that artifact;
6. add a mocked CPU contract test and an opt-in GPU smoke test;
7. defer counterfactual scoring until simulator snapshot/restore produces paired branches.

## Sources checked

- [StarWAM official repository](https://github.com/shaohua-pan/StarWAM)
- [StarWAM model repository](https://www.modelscope.cn/models/panshaohua/starwam)
- [LingBot-VA official repository](https://github.com/Robbyant/lingbot-va)
- [LingBot-VA LIBERO checkpoint](https://huggingface.co/robbyant/lingbot-va-posttrain-libero-long)
- [Fast-WAM official repository](https://github.com/yuantianyuan01/FastWAM)
- [Fast-WAM checkpoint](https://huggingface.co/yuanty/fastwam)

Repository metadata, README requirements, checkpoint visibility, and license fields were
checked on 2026-07-15. No checkpoint was downloaded or executed during this audit.
