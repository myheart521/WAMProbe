# Model store

Model weights are local artifacts and must never be committed to Git. WAMProbe mirrors
each upstream model repository under:

```text
checkpoints/upstream/<provider>/<owner>/<repository>/
```

Repository names and capitalization are preserved so that a path identifies exactly one
upstream source. The machine-readable pins live in
[`configs/models/upstream_models.json`](../configs/models/upstream_models.json).

## Download now

Only two sources are required for the first StarWAM adapter spike:

| Source | Download | Size | Target directory |
|---|---|---:|---|
| Wan2.2-TI2V-5B backbone | complete Hugging Face snapshot | 34.2 GB | `upstream/huggingface/Wan-AI/Wan2.2-TI2V-5B/` |
| StarWAM LIBERO MoT | MoT checkpoint plus `action_stats.json` | 12.0 GB | `upstream/modelscope/panshaohua/starwam/` |

Minimum model storage is approximately **46.3 GB**. Reserve at least **100 GB** for
download caches, simulator assets, and generated predictions.

### 1. Wan2.2-TI2V-5B

Source: [Wan-AI/Wan2.2-TI2V-5B](https://huggingface.co/Wan-AI/Wan2.2-TI2V-5B)

Pinned revision:

```text
921dbaf3f1674a56f47e83fb80a34bac8a8f203e
```

Download the complete repository into:

```text
/data/Project/MY/WAMProbe/checkpoints/upstream/huggingface/Wan-AI/Wan2.2-TI2V-5B/
```

Optional CLI command:

```bash
hf download Wan-AI/Wan2.2-TI2V-5B \
  --revision 921dbaf3f1674a56f47e83fb80a34bac8a8f203e \
  --local-dir checkpoints/upstream/huggingface/Wan-AI/Wan2.2-TI2V-5B
```

Do not rename the three `diffusion_pytorch_model-*.safetensors` shards, their index,
`Wan2.2_VAE.pth`, the T5 encoder, or tokenizer directories.

### 2. StarWAM LIBERO MoT

Source: [panshaohua/starwam](https://www.modelscope.cn/models/panshaohua/starwam)

Pinned Git revision:

```text
7d4bfe3ec76172ca17169fa959d21da099d386fe
```

The two required files, preserving their upstream relative paths, are:

```text
upstream/modelscope/panshaohua/starwam/
└── starwam-libero/
    ├── action_stats.json
    └── mot/
        └── starwam_wan225b_mot.pt
```

Expected checksums:

```text
d24edea01579880327cfd9dc84d24adab82e420dca9652e614ad697bc8cc5378  starwam-libero/mot/starwam_wan225b_mot.pt
9f65fb518ca446e0d5ca9e8127e960fe3d11e6466e4f48ba9bb1135b1e0fb4f0  starwam-libero/action_stats.json
```

You may download those two files manually. To use Git LFS while avoiding the optional
20 GB Shared-DiT payload:

```bash
GIT_LFS_SKIP_SMUDGE=1 git clone \
  https://www.modelscope.cn/panshaohua/starwam.git \
  checkpoints/upstream/modelscope/panshaohua/starwam

git -C checkpoints/upstream/modelscope/panshaohua/starwam \
  checkout 7d4bfe3ec76172ca17169fa959d21da099d386fe

git -C checkpoints/upstream/modelscope/panshaohua/starwam lfs pull \
  --include="starwam-libero/mot/starwam_wan225b_mot.pt"
```

## Optional later downloads

Do not download these for the first adapter spike:

| Model | Size | Target | Status |
|---|---:|---|---|
| StarWAM Shared-DiT checkpoint | 20.1 GB | `upstream/modelscope/panshaohua/starwam/starwam-libero/sharedit/` | optional second StarWAM family |
| LingBot-VA LIBERO-Long | 24.4 GB | `upstream/huggingface/robbyant/lingbot-va-posttrain-libero-long/` | second published-reference adapter |
| Fast-WAM LIBERO checkpoint | 12.0 GB | `upstream/huggingface/yuanty/fastwam/` | blocked until weight license metadata is explicit |

The LingBot-VA snapshot, when needed, is pinned to revision
`0e89d1e753019988aba484e8da2dc0810e264d9f`. Fast-WAM is listed in the manifest
for auditability but should not be downloaded yet.

## Placement rules

1. Keep the upstream directory layout and filenames unchanged.
2. Never mix files from two revisions in one repository directory.
3. Do not put source code, datasets, simulator assets, or experiment outputs here.
4. Do not commit model files, Hugging Face caches, Git LFS objects, or symlink targets.
5. A directory may be a symlink to another disk, but its path inside this repository must
   still follow the provider/owner/repository convention.
6. Record any approved revision change in `upstream_models.json` before running it.
7. Keep normalization statistics beside the checkpoint from which they were released.

After the required files are in place, run:

```bash
sha256sum \
  checkpoints/upstream/modelscope/panshaohua/starwam/starwam-libero/mot/starwam_wan225b_mot.pt \
  checkpoints/upstream/modelscope/panshaohua/starwam/starwam-libero/action_stats.json
```

WAMProbe will add `wamprobe doctor` as the next implementation slice to validate this
layout, revisions, required files, and checkpoint metadata without loading the GPU model.
