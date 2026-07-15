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

uv venv --python 3.11 environments/starwam/.venv

uv pip install --python environments/starwam/.venv/bin/python \
  torch==2.6.0 torchvision==0.21.0 torchaudio==2.6.0 \
  --index-url https://download.pytorch.org/whl/cu124

uv pip install --python environments/starwam/.venv/bin/python \
  -r vendor/upstream/starwam/examples/libero/requirements.txt

uv pip install --python environments/starwam/.venv/bin/python \
  -e vendor/upstream/starwam
```

`flash-attn` is an upstream requirement for some attention paths, but it should be built
only after the pinned PyTorch/CUDA environment succeeds:

```bash
environments/starwam/.venv/bin/python -m pip install flash-attn --no-build-isolation
```

The first proving step is metadata-only and must not deserialize an untrusted pickle. A
later checkpoint load must use upstream trusted code, `map_location="cpu"` or an explicit
device map, inference mode, deterministic seeds, and a recorded peak-memory measurement.

## Local paths

```text
vendor/upstream/starwam/
checkpoints/upstream/huggingface/Wan-AI/Wan2.2-TI2V-5B/
checkpoints/upstream/modelscope/panshaohua/starwam/
environments/starwam/.venv/
```

Only this environment documentation is tracked. The virtual environment, upstream source,
weights, caches, LIBERO assets, and predictions stay local.
