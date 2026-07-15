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
pure tensor mappings. It keeps LIBERO's separate legacy init-state compatibility path
unchanged. Do not generalize `weights_only=True` changes to arbitrary data or optimizer
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

This is a loadability check, not a successful LIBERO rollout or evidence that generated
actions are correct. The next gate is one typed observation-to-action artifact with its
resolved preprocessing and normalization metadata.

## Local paths

```text
vendor/upstream/starwam/
checkpoints/upstream/huggingface/Wan-AI/Wan2.2-TI2V-5B/
checkpoints/upstream/modelscope/panshaohua/starwam/
environments/starwam/.venv/
```

Only this environment documentation is tracked. The virtual environment, upstream source,
weights, caches, LIBERO assets, and predictions stay local.
