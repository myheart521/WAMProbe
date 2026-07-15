# Isolated StarWAM environment

StarWAM is intentionally isolated from WAMProbe's dependency-free core package. The first
adapter is pinned to upstream commit:

```text
f6c771fc3be0a9bc271ea4f1531d8ea35efb0ec7
```

Local upstream code belongs under `vendor/upstream/starwam/` and is ignored by Git and
package builds. Model files belong under `checkpoints/upstream/`; do not copy weights into
the source checkout.

## Reproduce the environment

```bash
git clone https://github.com/shaohua-pan/StarWAM.git vendor/upstream/starwam
git -C vendor/upstream/starwam checkout f6c771fc3be0a9bc271ea4f1531d8ea35efb0ec7
git -C vendor/upstream/starwam apply \
  "$(git rev-parse --show-toplevel)/environments/starwam/patches/0001-safe-inference-loads.patch"

uv venv --python 3.11 environments/starwam/.venv

uv pip install --python environments/starwam/.venv/bin/python \
  torch==2.6.0 torchvision==0.21.0 torchaudio==2.6.0 \
  --index-url https://download.pytorch.org/whl/cu124

uv pip install --python environments/starwam/.venv/bin/python \
  -r vendor/upstream/starwam/examples/libero/requirements.txt

uv pip install --python environments/starwam/.venv/bin/python \
  -e vendor/upstream/starwam
```

`flash-attn` is optional for some attention paths. Build it only if the selected path
actually imports it and after the pinned PyTorch/CUDA environment succeeds:

```bash
environments/starwam/.venv/bin/python -m pip install flash-attn --no-build-isolation
```

The tracked patch changes only model-inference checkpoint reads that were verified to be
pure tensor mappings. It also constructs UMT5 on the meta device before assigning its
memory-mapped weights, avoiding a duplicate random model on the GPU. The WAMProbe smoke
runner loads the pinned LIBERO NumPy init state with `weights_only=True` and a minimal
NumPy allowlist. Do not generalize these changes to arbitrary data or optimizer
checkpoints without inspecting their payloads first.

## Verified preflight

The pinned artifacts and environment passed the following checks on 2026-07-15:

- `wamprobe doctor --verify-hashes`: 2/2 required model groups passed, with no incomplete
  download fragments;
- environment: Python 3.11.15, PyTorch 2.6.0+cu124, four RTX 4090 GPUs, and 136 compatible
  installed packages;
- restricted metadata load: `weights_only=True`, `mmap=True`, and `map_location="meta"`
  for the StarWAM, Wan VAE, and Wan T5 checkpoints;
- StarWAM architecture contract: 3,300/3,300 state keys matched, with zero missing or
  unexpected keys;
- GPU 2 load-only smoke check: deterministic seed 42, `model.eval()`, 12.16 GB peak
  allocated and 12.38 GB peak reserved, followed by successful memory release.
- fixed LIBERO observation: `libero_spatial` task 0, init state 0, 30 wait steps, two
  256x256 RGB frames, eight ordered proprio values, and observation content SHA256
  `051ac984bcbfad0ecd0184f86e0c3b1d148502a849337132b438fbf62f22a29b`;
- real one-step action smoke: a denormalized `[32, 7]` chunk on an RTX 4090, 2.95 seconds
  model-call latency, 11.386 GiB peak allocated, and 11.529 GiB peak reserved. The VAE
  ran in FP32 on CPU while the released StarWAM action/DiT model ran in BF16 on GPU.
- released eight-step setting: the same typed `[32, 7]` path completed in 2.81 seconds
  with the same measured GPU peak and cache key
  `c6c46faab2a33940fe40d20aba3fab311f8e17885ed753f963c8b51161d939e1`.

These runs prove the typed observation-to-action integration path, not policy quality or
rollout success. No predicted action was executed in the simulator, so neither artifact
may be reported as a LIBERO benchmark result.

## Reproduce the fixed smoke run

Choose one physical GPU with sufficient free memory. Run T5 caching in a separate process
so its memory is fully released before the action model is loaded:

```bash
environments/starwam/.venv/bin/python environments/starwam/run_libero_smoke.py \
  --mode observe --gpu-index 0

environments/starwam/.venv/bin/python environments/starwam/run_libero_smoke.py \
  --mode text-cache --gpu-index 0 --minimum-free-gib 13

environments/starwam/.venv/bin/python environments/starwam/run_libero_smoke.py \
  --mode infer --gpu-index 0 --minimum-free-gib 15 \
  --num-inference-steps 8 --vae-device cpu
```

Add `--verify-large-hashes` to rehash the checkpoint, VAE, and T5 before a run. Generated
PNGs, text caches, observation metadata, and prediction JSON remain below
`runs/starwam-libero-smoke/` and are ignored by Git.

## Local paths

```text
vendor/upstream/starwam/
checkpoints/upstream/huggingface/Wan-AI/Wan2.2-TI2V-5B/
checkpoints/upstream/modelscope/panshaohua/starwam/
environments/starwam/.venv/
```

Only this environment documentation is tracked. The virtual environment, upstream source,
weights, caches, LIBERO assets, and predictions stay local.
