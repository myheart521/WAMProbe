#!/usr/bin/env python
"""Run one pinned LIBERO observation through the released StarWAM MoT policy.

The script is intentionally kept in the isolated StarWAM environment. It writes raw
observations, text caches, and prediction artifacts below ``runs/``, which is ignored by
Git. Run text-cache generation in a separate process before inference so its 11 GB T5
encoder is fully released before the action model is loaded.
"""

from __future__ import annotations

import argparse
import copy
import gc
import hashlib
import json
import math
import os
import random
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPOSITORY_ROOT / "src"
STARWAM_ROOT = REPOSITORY_ROOT / "vendor" / "upstream" / "starwam"
LIBERO_ROOT = REPOSITORY_ROOT / "vendor" / "upstream" / "libero"
BACKBONE_ROOT = (
    REPOSITORY_ROOT / "checkpoints" / "upstream" / "huggingface" / "Wan-AI" / "Wan2.2-TI2V-5B"
)
MODEL_ROOT = REPOSITORY_ROOT / "checkpoints" / "upstream" / "modelscope" / "panshaohua" / "starwam"
CHECKPOINT = MODEL_ROOT / "starwam-libero" / "mot" / "starwam_wan225b_mot.pt"
ACTION_STATS = MODEL_ROOT / "starwam-libero" / "action_stats.json"
VAE_CHECKPOINT = BACKBONE_ROOT / "Wan2.2_VAE.pth"
TEXT_ENCODER_CHECKPOINT = BACKBONE_ROOT / "models_t5_umt5-xxl-enc-bf16.pth"
RECIPE = (
    STARWAM_ROOT
    / "examples"
    / "libero"
    / "configs"
    / "recipes"
    / "starwam_libero_mot_wan22_5b.yaml"
)

STARWAM_REVISION = "f6c771fc3be0a9bc271ea4f1531d8ea35efb0ec7"
LIBERO_REVISION = "8f1084e3132a39270c3a13ebe37270a43ece2a01"
MODEL_REVISION = "7d4bfe3ec76172ca17169fa959d21da099d386fe"
BACKBONE_REVISION = "921dbaf3f1674a56f47e83fb80a34bac8a8f203e"
CHECKPOINT_SHA256 = "d24edea01579880327cfd9dc84d24adab82e420dca9652e614ad697bc8cc5378"
ACTION_STATS_SHA256 = "9f65fb518ca446e0d5ca9e8127e960fe3d11e6466e4f48ba9bb1135b1e0fb4f0"
VAE_SHA256 = "20eb789667fa5e60e7516bf509512f6cb61f01b0aa0695eadaea930c13892b36"
TEXT_ENCODER_SHA256 = "7cace0da2b446bbbbc57d031ab6cf163a3d59b366da94e5afe36745b746fd81d"

TASK_SUITE = "libero_spatial"
TASK_ID = 0
INIT_STATE_INDEX = 0
WAIT_STEPS = 30
SEED = 42
TASK = "pick up the black bowl between the plate and the ramekin and place it on the plate"
CONTEXT_ID = "libero-spatial-task0-init0-wait30"
BDDL_SHA256 = "9b59eb1287802868ad9bc78d58e6d36d4ba31134e679cfdbdf4b0feb660c959b"
INIT_STATES_SHA256 = "cbbc73792ce546c9bec181fd328a411d3183074840b282671dee481511381d0a"
TEXT_PROMPT_TEMPLATE = (
    "A video recorded from a robot's point of view executing the following instruction: {task}"
)
CAMERA_ORDER = ("agentview", "wrist")
PROPRIO_FIELDS = (
    "eef_x",
    "eef_y",
    "eef_z",
    "axis_angle_x",
    "axis_angle_y",
    "axis_angle_z",
    "gripper_qpos_0",
    "gripper_qpos_1",
)
LIBERO_DUMMY_ACTION = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, -1.0]

if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from wamprobe.adapters.starwam import (  # noqa: E402
    StarWAMAdapter,
    StarWAMBackendResult,
    StarWAMRelease,
)
from wamprobe.api.robotics import InferenceRuntime, RGBFrame, RobotObservation  # noqa: E402
from wamprobe.artifacts import (  # noqa: E402
    ActionPredictionArtifact,
    ModelProvenance,
    ResolvedInference,
    ResolvedPreprocessing,
)
from wamprobe.libero_cf import LiberoTaskSpec, load_libero_cf_manifest  # noqa: E402

LIBERO_CF_MANIFEST = REPOSITORY_ROOT / "configs" / "benchmarks" / "libero_cf_mini_v0.1.json"


@dataclass(frozen=True, slots=True)
class CapturedObservation:
    """One fixed simulator observation plus benchmark provenance."""

    observation: RobotObservation
    done_during_wait: bool
    bddl_path: Path
    init_states_path: Path
    init_states_shape: tuple[int, ...]
    init_states_dtype: str


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(8 * 1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def _git_revision(path: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _verify_revision(path: Path, expected: str, label: str) -> None:
    actual = _git_revision(path)
    if actual != expected:
        raise RuntimeError(f"{label} revision mismatch: expected {expected}, got {actual}")


def _verify_huggingface_revision(path: Path, expected: str) -> None:
    metadata = path / ".cache" / "huggingface" / "download" / "Wan2.2_VAE.pth.metadata"
    if not metadata.is_file():
        raise FileNotFoundError(f"missing Hugging Face revision metadata: {metadata}")
    actual = metadata.read_text(encoding="utf-8").splitlines()[0]
    if actual != expected:
        raise RuntimeError(f"Wan2.2 revision mismatch: expected {expected}, got {actual}")


def _verify_inputs(*, verify_large_hashes: bool) -> None:
    required = (CHECKPOINT, ACTION_STATS, VAE_CHECKPOINT, TEXT_ENCODER_CHECKPOINT, RECIPE)
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"missing required files: {missing}")
    _verify_revision(STARWAM_ROOT, STARWAM_REVISION, "StarWAM")
    _verify_revision(LIBERO_ROOT, LIBERO_REVISION, "LIBERO")
    _verify_revision(MODEL_ROOT, MODEL_REVISION, "StarWAM model")
    _verify_huggingface_revision(BACKBONE_ROOT, BACKBONE_REVISION)
    if _sha256(ACTION_STATS) != ACTION_STATS_SHA256:
        raise RuntimeError("released action/state statistics hash mismatch")
    if verify_large_hashes:
        expected_hashes = {
            CHECKPOINT: CHECKPOINT_SHA256,
            VAE_CHECKPOINT: VAE_SHA256,
            TEXT_ENCODER_CHECKPOINT: TEXT_ENCODER_SHA256,
        }
        for path, expected in expected_hashes.items():
            actual = _sha256(path)
            if actual != expected:
                raise RuntimeError(f"hash mismatch for {path}: expected {expected}, got {actual}")


def _configure_process(gpu_index: int, run_dir: Path) -> None:
    os.environ["CUDA_VISIBLE_DEVICES"] = str(gpu_index)
    os.environ["MUJOCO_EGL_DEVICE_ID"] = str(gpu_index)
    os.environ.setdefault("MUJOCO_GL", "egl")
    os.environ.setdefault("PYOPENGL_PLATFORM", "egl")
    config_dir = run_dir / "libero_config"
    config_dir.mkdir(parents=True, exist_ok=True)
    os.environ["LIBERO_CONFIG_PATH"] = str(config_dir)

    benchmark_root = LIBERO_ROOT / "libero" / "libero"
    config = {
        "benchmark_root": str(benchmark_root),
        "bddl_files": str(benchmark_root / "bddl_files"),
        "init_states": str(benchmark_root / "init_files"),
        "datasets": str(LIBERO_ROOT / "libero" / "datasets"),
        "assets": str(benchmark_root / "assets"),
    }
    config_path = config_dir / "config.yaml"
    config_path.write_text(
        "".join(f"{key}: {json.dumps(value)}\n" for key, value in config.items()),
        encoding="utf-8",
    )
    for path in (STARWAM_ROOT, LIBERO_ROOT):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))


def _set_seed(seed: int) -> None:
    import numpy as np
    import torch

    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True


def _require_cuda_memory(minimum_free_gib: float) -> Any:
    import torch

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is required for the released 5B StarWAM smoke test")
    device = torch.device("cuda:0")
    torch.cuda.set_device(device)
    free_bytes, total_bytes = torch.cuda.mem_get_info(device)
    minimum_bytes = int(minimum_free_gib * 1024**3)
    if free_bytes < minimum_bytes:
        raise RuntimeError(
            f"insufficient free VRAM: need {minimum_free_gib:.1f} GiB, "
            f"have {free_bytes / 1024**3:.1f} GiB"
        )
    print(
        json.dumps(
            {
                "cuda_device": torch.cuda.get_device_name(device),
                "free_gib": round(free_bytes / 1024**3, 2),
                "total_gib": round(total_bytes / 1024**3, 2),
            },
            sort_keys=True,
        )
    )
    return device


def _quat_to_axis_angle(quaternion: Any) -> Any:
    import numpy as np

    quat = np.asarray(quaternion, dtype=np.float32).copy()
    quat[3] = np.clip(quat[3], -1.0, 1.0)
    denominator = math.sqrt(max(0.0, 1.0 - float(quat[3]) ** 2))
    if math.isclose(denominator, 0.0):
        return np.zeros(3, dtype=np.float32)
    angle = 2.0 * math.acos(float(quat[3]))
    return (quat[:3] * angle / denominator).astype(np.float32)


def _load_init_states(path: Path) -> Any:
    """Load the pinned NumPy array with a minimal weights-only allowlist."""

    import numpy as np
    import torch
    from numpy.core.multiarray import _reconstruct  # type: ignore[attr-defined]

    safe_globals = [_reconstruct, np.ndarray, np.dtype, np.dtypes.Float64DType]
    with torch.serialization.safe_globals(safe_globals):
        states = torch.load(path, map_location="cpu", weights_only=True)
    if not isinstance(states, np.ndarray) or states.dtype != np.float64:
        raise TypeError("LIBERO init states must be a float64 NumPy array")
    return states


def _capture_observation(spec: LiberoTaskSpec | None = None) -> CapturedObservation:
    import numpy as np
    from libero.libero import benchmark, get_libero_path
    from libero.libero.envs import OffScreenRenderEnv

    task_suite = spec.task_suite if spec is not None else TASK_SUITE
    task_id = spec.task_id if spec is not None else TASK_ID
    task_text = spec.task if spec is not None else TASK
    init_state_index = spec.init_state_index if spec is not None else INIT_STATE_INDEX
    wait_steps = spec.wait_steps if spec is not None else WAIT_STEPS
    seed = spec.seed if spec is not None else SEED
    context_id = spec.context_id if spec is not None else CONTEXT_ID
    bddl_sha256 = spec.bddl_sha256 if spec is not None else BDDL_SHA256
    init_states_sha256 = spec.init_states_sha256 if spec is not None else INIT_STATES_SHA256
    expected_shape = spec.init_states_shape if spec is not None else (50, 92)

    suite = benchmark.get_benchmark_dict()[task_suite]()
    task = suite.get_task(task_id)
    if task.language != task_text:
        raise RuntimeError(
            f"pinned LIBERO task changed: expected {task_text!r}, got {task.language!r}"
        )

    bddl_path = Path(suite.get_task_bddl_file_path(TASK_ID))
    init_states_path = (
        Path(get_libero_path("init_states")) / task.problem_folder / task.init_states_file
    )
    if _sha256(bddl_path) != bddl_sha256:
        raise RuntimeError("LIBERO BDDL hash mismatch")
    if _sha256(init_states_path) != init_states_sha256:
        raise RuntimeError("LIBERO init-state hash mismatch")
    init_states = _load_init_states(init_states_path)
    if init_states.shape != expected_shape:
        raise RuntimeError(f"unexpected LIBERO init-state shape: {init_states.shape}")

    environment = OffScreenRenderEnv(
        bddl_file_name=str(bddl_path),
        camera_heights=256,
        camera_widths=256,
    )
    environment.seed(seed)
    done = False
    try:
        environment.reset()
        observation = environment.set_init_state(init_states[init_state_index])
        for _ in range(wait_steps):
            observation, _, done, _ = environment.step(LIBERO_DUMMY_ACTION)
    finally:
        environment.close()

    agentview = np.ascontiguousarray(observation["agentview_image"], dtype=np.uint8)
    wrist = np.ascontiguousarray(observation["robot0_eye_in_hand_image"], dtype=np.uint8)
    proprio = np.concatenate(
        [
            np.asarray(observation["robot0_eef_pos"], dtype=np.float32),
            _quat_to_axis_angle(observation["robot0_eef_quat"]),
            np.asarray(observation["robot0_gripper_qpos"], dtype=np.float32),
        ]
    )
    if proprio.shape != (8,):
        raise RuntimeError(f"unexpected LIBERO proprio shape: {proprio.shape}")

    typed_observation = RobotObservation(
        context_id=context_id,
        task=task_text,
        frames=(
            RGBFrame("agentview", 256, 256, agentview.tobytes()),
            RGBFrame("wrist", 256, 256, wrist.tobytes()),
        ),
        proprio=tuple(float(value) for value in proprio),
        proprio_fields=PROPRIO_FIELDS,
    )
    return CapturedObservation(
        observation=typed_observation,
        done_during_wait=bool(done),
        bddl_path=bddl_path,
        init_states_path=init_states_path,
        init_states_shape=tuple(int(value) for value in init_states.shape),
        init_states_dtype=str(init_states.dtype),
    )


def _resolved_config(run_dir: Path) -> Any:
    from starwam.config import load_config

    config = load_config(str(RECIPE))
    config.backbone.pretrained_model_id = str(BACKBONE_ROOT)
    config.backbone.load_text_encoder = False
    config.framework.action_expert_init_from = None
    config.data.action_stats_path = str(ACTION_STATS)
    config.data.state_stats_path = str(ACTION_STATS)
    config.data.text_embedding_cache_dir = str(run_dir / "text_embedding_cache")
    return config


def _text_cache_path(config: Any, task: str = TASK) -> Path:
    from starwam.data.lerobot import text_cache_path

    return text_cache_path(
        config.data.text_embedding_cache_dir,
        task,
        int(config.data.text_len),
        TEXT_PROMPT_TEMPLATE,
        str(config.data.text_cache_encoder_id),
    )


def _load_text_cache(path: Path, config: Any, task: str = TASK) -> tuple[Any, Any]:
    import torch

    payload = torch.load(path, map_location="cpu", weights_only=True)
    if not isinstance(payload, dict):
        raise TypeError("text cache must contain a mapping")
    if payload.get("task") != task or payload.get("prompt") != TEXT_PROMPT_TEMPLATE.format(
        task=task
    ):
        raise RuntimeError("text cache task or prompt mismatch")
    context = payload.get("context")
    mask = payload.get("mask")
    if not isinstance(context, torch.Tensor) or not isinstance(mask, torch.Tensor):
        raise TypeError("text cache context and mask must be tensors")
    expected_shape = (int(config.data.text_len), 4096)
    if tuple(context.shape) != expected_shape or tuple(mask.shape) != (expected_shape[0],):
        raise RuntimeError(
            f"text cache shape mismatch: context={tuple(context.shape)} mask={tuple(mask.shape)}"
        )
    return context, mask


def _text_condition_sha256(context: Any, mask: Any, task: str = TASK) -> str:
    import torch

    metadata = {
        "task": task,
        "prompt": TEXT_PROMPT_TEMPLATE.format(task=task),
        "context_shape": list(context.shape),
        "context_dtype": str(context.dtype),
        "mask_shape": list(mask.shape),
        "mask_dtype": str(mask.dtype),
    }
    digest = hashlib.sha256(
        json.dumps(metadata, separators=(",", ":"), sort_keys=True).encode("utf-8")
    )
    digest.update(context.detach().cpu().contiguous().view(torch.uint8).numpy().tobytes())
    digest.update(mask.detach().cpu().contiguous().view(torch.uint8).numpy().tobytes())
    return digest.hexdigest()


def _prepare_text_caches(
    config: Any,
    minimum_free_gib: float,
    tasks: tuple[str, ...],
) -> tuple[Path, ...]:
    import torch
    from starwam.backbone.wan22 import Wan22TextEncoder
    from starwam.data.lerobot import save_text_cache

    cache_paths = tuple(_text_cache_path(config, task) for task in tasks)
    missing = [
        (task, path) for task, path in zip(tasks, cache_paths, strict=True) if not path.is_file()
    ]
    for task, path in zip(tasks, cache_paths, strict=True):
        if path.is_file():
            _load_text_cache(path, config, task)
            print(f"text cache already valid: {path}")
    if not missing:
        return cache_paths

    device = _require_cuda_memory(minimum_free_gib)
    _set_seed(SEED)
    encoder = Wan22TextEncoder(
        ckpt_path=str(TEXT_ENCODER_CHECKPOINT),
        tokenizer_path=str(BACKBONE_ROOT / "google" / "umt5-xxl"),
        text_len=int(config.data.text_len),
        device=str(device),
        dtype=torch.bfloat16,
    )
    try:
        for task, cache_path in missing:
            prompt = TEXT_PROMPT_TEMPLATE.format(task=task)
            with torch.inference_mode():
                contexts, masks = encoder.encode([prompt])
            save_text_cache(
                cache_path,
                contexts[0],
                masks[0],
                prompt,
                task,
            )
            _load_text_cache(cache_path, config, task)
            print(f"wrote text cache: {cache_path}")
    finally:
        del encoder
        gc.collect()
        torch.cuda.empty_cache()
    return cache_paths


def _prepare_text_cache(config: Any, minimum_free_gib: float) -> Path:
    """Backward-compatible single-task text-cache helper."""

    return _prepare_text_caches(config, minimum_free_gib, (TASK,))[0]


def _preprocessing(text_cache_sha256: str, task: str = TASK) -> ResolvedPreprocessing:
    return ResolvedPreprocessing(
        camera_order=CAMERA_ORDER,
        camera_transforms=("rotate_180", "rotate_180"),
        source_size=(256, 256),
        resized_camera_size=(224, 224),
        model_size=(224, 448),
        resize_interpolation="PIL_BILINEAR",
        channel_order="RGB",
        tensor_layout="BCHW",
        camera_concatenation="horizontal",
        input_value_range=(-1.0, 1.0),
        text_prompt=TEXT_PROMPT_TEMPLATE.format(task=task),
        text_cache_sha256=text_cache_sha256,
        proprio_fields=PROPRIO_FIELDS,
        action_normalization="minmax_then_libero_gripper_binary_inversion",
        action_stats_sha256=ACTION_STATS_SHA256,
    )


def _preprocess_frames(observation: RobotObservation, preprocessing: ResolvedPreprocessing) -> Any:
    import numpy as np
    from PIL import Image

    frames = {frame.camera_name: frame for frame in observation.frames}
    resized = []
    target_height, target_width = preprocessing.resized_camera_size
    for camera_name, transform in zip(
        preprocessing.camera_order, preprocessing.camera_transforms, strict=True
    ):
        frame = frames[camera_name]
        image = np.frombuffer(frame.data, dtype=np.uint8).reshape(frame.height, frame.width, 3)
        if transform == "rotate_180":
            image = np.ascontiguousarray(image[::-1, ::-1])
        resized.append(
            np.asarray(
                Image.fromarray(image).resize(
                    (target_width, target_height), resample=Image.Resampling.BILINEAR
                ),
                dtype=np.uint8,
            )
        )
    axis = 1 if preprocessing.camera_concatenation == "horizontal" else 0
    model_image = np.ascontiguousarray(np.concatenate(resized, axis=axis))
    if tuple(model_image.shape) != (*preprocessing.model_size, 3):
        raise RuntimeError(f"preprocessed image has unexpected shape {model_image.shape}")
    return model_image


def _write_observation(
    captured: CapturedObservation,
    preprocessing: ResolvedPreprocessing,
    run_dir: Path,
    spec: LiberoTaskSpec | None = None,
) -> Path:
    import numpy as np
    from PIL import Image

    task_suite = spec.task_suite if spec is not None else TASK_SUITE
    task_id = spec.task_id if spec is not None else TASK_ID
    init_state_index = spec.init_state_index if spec is not None else INIT_STATE_INDEX
    wait_steps = spec.wait_steps if spec is not None else WAIT_STEPS
    seed = spec.seed if spec is not None else SEED
    bddl_sha256 = spec.bddl_sha256 if spec is not None else BDDL_SHA256
    init_states_sha256 = spec.init_states_sha256 if spec is not None else INIT_STATES_SHA256
    output_dir = run_dir / "observations" / captured.observation.context_id
    output_dir.mkdir(parents=True, exist_ok=True)
    for frame in captured.observation.frames:
        image = np.frombuffer(frame.data, dtype=np.uint8).reshape(frame.height, frame.width, 3)
        Image.fromarray(image).save(output_dir / f"{frame.camera_name}.png")
    Image.fromarray(_preprocess_frames(captured.observation, preprocessing)).save(
        output_dir / "model_input.png"
    )
    metadata = {
        "observation": captured.observation.descriptor(),
        "preprocessing": preprocessing.to_dict(),
        "libero": {
            "revision": LIBERO_REVISION,
            "task_suite": task_suite,
            "task_id": task_id,
            "init_state_index": init_state_index,
            "wait_steps": wait_steps,
            "seed": seed,
            "done_during_wait": captured.done_during_wait,
            "bddl_path": str(captured.bddl_path),
            "bddl_sha256": bddl_sha256,
            "init_states_path": str(captured.init_states_path),
            "init_states_sha256": init_states_sha256,
            "init_states_shape": list(captured.init_states_shape),
            "init_states_dtype": captured.init_states_dtype,
        },
    }
    metadata_path = output_dir / "observation.json"
    metadata_path.write_text(
        json.dumps(metadata, allow_nan=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"wrote observation: {metadata_path}")
    return metadata_path


def _load_stats() -> dict[str, dict[str, Any]]:
    import torch

    payload = json.loads(ACTION_STATS.read_text(encoding="utf-8"))
    output: dict[str, dict[str, Any]] = {}
    for group in ("action", "state"):
        values = payload.get(group)
        if not isinstance(values, dict):
            raise TypeError(f"missing statistics group: {group}")
        output[group] = {
            key: torch.tensor(value, dtype=torch.float32)
            for key, value in values.items()
            if key in {"min", "max", "mean", "std"}
        }
    return output


def _normalize_proprio(proprio: Any, stats: dict[str, Any]) -> Any:
    state_min = stats["min"][: proprio.shape[-1]].to(dtype=proprio.dtype)
    state_max = stats["max"][: proprio.shape[-1]].to(dtype=proprio.dtype)
    normalized = 2.0 * (proprio - state_min) / (state_max - state_min).clamp_min(1e-6) - 1.0
    return normalized.clamp(-5.0, 5.0)


def _denormalize_actions(actions: Any, stats: dict[str, Any]) -> Any:
    import numpy as np

    action = actions.detach().float().cpu()
    action_min = stats["min"]
    action_max = stats["max"]
    denormalized = (action.clamp(-1.0, 1.0) + 1.0) * 0.5 * (action_max - action_min).clamp_min(
        1e-6
    ) + action_min
    output = denormalized.numpy()
    if output.ndim == 3:
        output = output[0]
    if output.shape != (32, 7):
        raise RuntimeError(f"StarWAM returned unexpected action shape: {output.shape}")
    output[..., -1] = np.where(output[..., -1] > 0.5, -1.0, 1.0)
    return output.astype(np.float32)


def _build_model(config: Any, device: Any, vae_device: str) -> Any:
    import torch
    from starwam import build_framework
    from starwam.backbone.wan22 import Wan22VAE
    from starwam.modules.scheduler import FlowMatchScheduler

    model_config = copy.deepcopy(config)
    model_config.backbone.pretrained_model_id = str(
        REPOSITORY_ROOT / "runs" / "starwam-libero-smoke" / "no-eager-backbone-load"
    )
    model_config.framework.action_expert_init_from = None

    original_stats = FlowMatchScheduler._precompute_training_weight_stats

    def cpu_scheduler_stats(scheduler: Any) -> tuple[float, float]:
        with torch.device("cpu"):
            return original_stats(scheduler)

    if hasattr(torch.__future__, "set_swap_module_params_on_conversion"):
        torch.__future__.set_swap_module_params_on_conversion(True)
    FlowMatchScheduler._precompute_training_weight_stats = cpu_scheduler_stats
    try:
        with torch.device("meta"):
            model = build_framework(model_config, device="meta", dtype=torch.bfloat16)
    finally:
        FlowMatchScheduler._precompute_training_weight_stats = original_stats

    state = torch.load(CHECKPOINT, map_location="cpu", weights_only=True, mmap=True)
    result = model.load_state_dict(state, strict=True, assign=True)
    if result.missing_keys or result.unexpected_keys:
        raise RuntimeError(
            f"checkpoint mismatch: missing={result.missing_keys} "
            f"unexpected={result.unexpected_keys}"
        )
    model.to(device=device, dtype=torch.bfloat16)
    del state
    gc.collect()

    model.backbone.vae = Wan22VAE(
        vae_pth=str(VAE_CHECKPOINT),
        device=vae_device,
        dtype=torch.float32,
        in_channels=48,
    )
    model.eval()
    return model


class LocalStarWAMBackend:
    """Heavy runtime seam consumed by the dependency-free StarWAM adapter."""

    def __init__(
        self,
        model: Any,
        config: Any,
        context: Any,
        context_mask: Any,
        stats: dict[str, dict[str, Any]],
        preprocessing: ResolvedPreprocessing,
        device: Any,
        runtime_device: str,
        num_inference_steps: int,
    ) -> None:
        self.model = model
        self.config = config
        self.context = context
        self.context_mask = context_mask
        self.stats = stats
        self.preprocessing = preprocessing
        self.device = device
        self.runtime_device = runtime_device
        self.num_inference_steps = num_inference_steps

    def infer_action(self, observation: RobotObservation, *, seed: int) -> StarWAMBackendResult:
        import torch

        image = _preprocess_frames(observation, self.preprocessing)
        input_image = (
            torch.as_tensor(image, dtype=torch.float32).permute(2, 0, 1).unsqueeze(0)
            * (2.0 / 255.0)
            - 1.0
        ).to(device=self.device, dtype=torch.bfloat16)
        proprio = torch.tensor(observation.proprio, dtype=torch.float32).view(1, 8)
        proprio = _normalize_proprio(proprio, self.stats["state"]).to(
            device=self.device, dtype=torch.bfloat16
        )

        torch.cuda.reset_peak_memory_stats(self.device)
        torch.cuda.synchronize(self.device)
        start = time.perf_counter()
        with torch.inference_mode():
            prediction = self.model.infer_action(
                input_image=input_image,
                context=self.context,
                context_mask=self.context_mask,
                action_horizon=int(self.config.framework.chunk_size),
                num_inference_steps=self.num_inference_steps,
                seed=seed,
                proprio=proprio,
                num_video_frames=9,
            )
        torch.cuda.synchronize(self.device)
        latency = time.perf_counter() - start
        denormalized = _denormalize_actions(prediction, self.stats["action"])
        runtime = InferenceRuntime(
            device=self.runtime_device,
            dtype="bfloat16",
            latency_seconds=latency,
            peak_allocated_bytes=torch.cuda.max_memory_allocated(self.device),
            peak_reserved_bytes=torch.cuda.max_memory_reserved(self.device),
        )
        return StarWAMBackendResult(
            actions=tuple(tuple(float(value) for value in row) for row in denormalized),
            runtime=runtime,
        )

    def close(self) -> None:
        import torch

        self.model = None
        self.context = None
        self.context_mask = None
        gc.collect()
        torch.cuda.empty_cache()


def _run_inference(
    config: Any,
    run_dir: Path,
    minimum_free_gib: float,
    num_inference_steps: int,
    vae_device: str,
    physical_gpu_index: int,
) -> Path:
    import torch

    text_cache_path = _text_cache_path(config)
    if not text_cache_path.is_file():
        raise FileNotFoundError(
            f"missing text cache {text_cache_path}; run --mode text-cache first"
        )
    context, context_mask = _load_text_cache(text_cache_path, config)
    preprocessing = _preprocessing(_text_condition_sha256(context, context_mask))
    captured = _capture_observation()
    _write_observation(captured, preprocessing, run_dir)

    device = _require_cuda_memory(minimum_free_gib)
    _set_seed(SEED)
    context = context.unsqueeze(0).to(device=device, dtype=torch.bfloat16)
    context_mask = context_mask.unsqueeze(0).to(device=device, dtype=torch.bool)
    model = _build_model(config, device, vae_device)
    backend = LocalStarWAMBackend(
        model=model,
        config=config,
        context=context,
        context_mask=context_mask,
        stats=_load_stats(),
        preprocessing=preprocessing,
        device=device,
        runtime_device=(
            f"cuda:0 (physical GPU {physical_gpu_index}, {torch.cuda.get_device_name(device)})"
        ),
        num_inference_steps=num_inference_steps,
    )
    adapter = StarWAMAdapter(backend, release=StarWAMRelease())
    try:
        prediction = adapter.predict_action(captured.observation, seed=SEED)
        artifact = ActionPredictionArtifact(
            observation=captured.observation,
            prediction=prediction,
            provenance=ModelProvenance(
                adapter_version="0.1.0a0",
                upstream_code_revision=STARWAM_REVISION,
                model_revision=MODEL_REVISION,
                backbone_revision=BACKBONE_REVISION,
                checkpoint_sha256=CHECKPOINT_SHA256,
                vae_sha256=VAE_SHA256,
                text_encoder_sha256=TEXT_ENCODER_SHA256,
            ),
            preprocessing=preprocessing,
            inference=ResolvedInference(
                engine="starwam_mot_infer_action",
                num_inference_steps=num_inference_steps,
                scheduler="continuous_flow_match_euler",
                scheduler_shift=float(config.framework.action_scheduler.infer_shift),
                video_conditioning=str(config.framework.action_video_conditioning),
                vae_device=vae_device,
                sampled_video_frames=9,
            ),
        )
        output = run_dir / "predictions" / f"{artifact.cache_key}.json"
        artifact.write_json(output)
        print(
            json.dumps(
                {
                    "prediction_artifact": str(output),
                    "cache_key": artifact.cache_key,
                    "action_shape": [prediction.horizon, prediction.action_dim],
                    "latency_seconds": prediction.runtime.latency_seconds,
                    "peak_allocated_gib": round(
                        prediction.runtime.peak_allocated_bytes / 1024**3, 3
                    ),
                    "peak_reserved_gib": round(prediction.runtime.peak_reserved_bytes / 1024**3, 3),
                },
                indent=2,
                sort_keys=True,
            )
        )
        return output
    finally:
        adapter.close()


def _provenance() -> ModelProvenance:
    return ModelProvenance(
        adapter_version="0.1.0a0",
        upstream_code_revision=STARWAM_REVISION,
        model_revision=MODEL_REVISION,
        backbone_revision=BACKBONE_REVISION,
        checkpoint_sha256=CHECKPOINT_SHA256,
        vae_sha256=VAE_SHA256,
        text_encoder_sha256=TEXT_ENCODER_SHA256,
    )


def _inference_configuration(
    config: Any,
    *,
    num_inference_steps: int,
    vae_device: str,
) -> ResolvedInference:
    return ResolvedInference(
        engine="starwam_mot_infer_action",
        num_inference_steps=num_inference_steps,
        scheduler="continuous_flow_match_euler",
        scheduler_shift=float(config.framework.action_scheduler.infer_shift),
        video_conditioning=str(config.framework.action_video_conditioning),
        vae_device=vae_device,
        sampled_video_frames=9,
    )


def _matrix_cache_key(
    observation: RobotObservation,
    preprocessing: ResolvedPreprocessing,
    inference: ResolvedInference,
    *,
    seed: int,
) -> str:
    payload = {
        "schema_version": "0.1",
        "observation": observation.descriptor(),
        "model_id": StarWAMRelease().model_id,
        "seed": seed,
        "provenance": _provenance().to_dict(),
        "preprocessing": preprocessing.to_dict(),
        "inference": inference.to_dict(),
    }
    return hashlib.sha256(
        json.dumps(
            payload,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()


def _cached_prediction(path: Path, cache_key: str) -> dict[str, object] | None:
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict) or payload.get("cache_key") != cache_key:
            return None
        prediction = payload["prediction"]
        if not isinstance(prediction, dict):
            return None
        prediction_sha256 = payload.get("prediction_sha256")
        if (
            prediction_sha256
            != hashlib.sha256(
                json.dumps(
                    prediction,
                    allow_nan=False,
                    ensure_ascii=False,
                    separators=(",", ":"),
                    sort_keys=True,
                ).encode("utf-8")
            ).hexdigest()
        ):
            return None
        actions = prediction["actions"]
        runtime = prediction["runtime"]
        if not isinstance(actions, list) or len(actions) != 32:
            return None
        if not all(
            isinstance(action, list)
            and len(action) == 7
            and all(
                isinstance(value, (int, float))
                and not isinstance(value, bool)
                and math.isfinite(float(value))
                for value in action
            )
            for action in actions
        ):
            return None
        if not isinstance(runtime, dict):
            return None
        return payload
    except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError):
        return None


def _matrix_record(
    *,
    spec: LiberoTaskSpec,
    seed: int,
    num_inference_steps: int,
    cache_key: str,
    path: Path,
    payload: dict[str, object],
    status: str,
) -> dict[str, object]:
    prediction = payload["prediction"]
    if not isinstance(prediction, dict):
        raise TypeError("prediction payload must be an object")
    runtime = prediction["runtime"]
    actions = prediction["actions"]
    if not isinstance(runtime, dict) or not isinstance(actions, list):
        raise TypeError("prediction runtime and actions have invalid types")
    return {
        "task_key": spec.key,
        "task_family": spec.task_family,
        "context_id": spec.context_id,
        "seed": seed,
        "num_inference_steps": num_inference_steps,
        "cache_key": cache_key,
        "prediction_artifact": str(path),
        "status": status,
        "action_horizon": len(actions),
        "action_dim": len(actions[0]) if actions else 0,
        "latency_seconds": runtime.get("latency_seconds"),
        "peak_allocated_bytes": runtime.get("peak_allocated_bytes"),
        "peak_reserved_bytes": runtime.get("peak_reserved_bytes"),
    }


def _write_matrix_index(
    run_dir: Path,
    *,
    manifest_path: Path,
    task_keys: list[str],
    seeds: tuple[int, ...],
    inference_steps: tuple[int, ...],
    records: list[dict[str, object]],
) -> None:
    path = run_dir / "matrix-index.json"
    payload = {
        "schema_version": "0.1",
        "benchmark_id": "libero-cf-mini-v0.1",
        "model_id": StarWAMRelease().model_id,
        "manifest_uri": str(manifest_path),
        "manifest_sha256": _sha256(manifest_path),
        "task_keys": task_keys,
        "seeds": list(seeds),
        "num_inference_steps": list(inference_steps),
        "expected_predictions": len(task_keys) * len(seeds) * len(inference_steps),
        "completed_predictions": sum(
            record.get("status") in {"generated", "cache-hit"} for record in records
        ),
        "failed_predictions": sum(record.get("status") == "failed" for record in records),
        "records": records,
        "capability_skips": [
            {
                "ablation": "candidate-action-mask",
                "status": "skipped",
                "reason": (
                    "released StarWAM adapter predicts actions from observation/task and "
                    "does not accept a candidate action as model input"
                ),
            },
            {
                "ablation": "candidate-action-shuffle",
                "status": "skipped",
                "reason": ("released StarWAM adapter has no action-conditioned future endpoint"),
            },
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        temporary.write_text(
            json.dumps(payload, allow_nan=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def _run_inference_matrix(
    config: Any,
    run_dir: Path,
    *,
    manifest_path: Path,
    task_keys: list[str],
    seeds: tuple[int, ...],
    inference_steps: tuple[int, ...],
    minimum_free_gib: float,
    vae_device: str,
    physical_gpu_index: int,
) -> Path:
    import torch

    manifest = load_libero_cf_manifest(manifest_path)
    if manifest.libero_revision != LIBERO_REVISION:
        raise RuntimeError("LIBERO-CF manifest and StarWAM runner revisions differ")
    specs = manifest.select(task_keys)
    _prepare_text_caches(
        config,
        minimum_free_gib,
        tuple(spec.task for spec in specs),
    )

    prepared: dict[
        str,
        tuple[CapturedObservation, ResolvedPreprocessing, Any, Any],
    ] = {}
    for spec in specs:
        text_path = _text_cache_path(config, spec.task)
        context, context_mask = _load_text_cache(text_path, config, spec.task)
        preprocessing = _preprocessing(
            _text_condition_sha256(context, context_mask, spec.task),
            spec.task,
        )
        captured = _capture_observation(spec)
        _write_observation(captured, preprocessing, run_dir, spec)
        prepared[spec.key] = (captured, preprocessing, context, context_mask)

    records: list[dict[str, object]] = []
    jobs: list[
        tuple[
            LiberoTaskSpec,
            CapturedObservation,
            ResolvedPreprocessing,
            Any,
            Any,
            int,
            int,
            str,
            Path,
        ]
    ] = []
    for spec in specs:
        captured, preprocessing, context, context_mask = prepared[spec.key]
        for num_inference_steps in inference_steps:
            inference = _inference_configuration(
                config,
                num_inference_steps=num_inference_steps,
                vae_device=vae_device,
            )
            for seed in seeds:
                cache_key = _matrix_cache_key(
                    captured.observation,
                    preprocessing,
                    inference,
                    seed=seed,
                )
                path = run_dir / "predictions" / f"{cache_key}.json"
                cached = _cached_prediction(path, cache_key)
                if cached is not None:
                    records.append(
                        _matrix_record(
                            spec=spec,
                            seed=seed,
                            num_inference_steps=num_inference_steps,
                            cache_key=cache_key,
                            path=path,
                            payload=cached,
                            status="cache-hit",
                        )
                    )
                else:
                    jobs.append(
                        (
                            spec,
                            captured,
                            preprocessing,
                            context,
                            context_mask,
                            num_inference_steps,
                            seed,
                            cache_key,
                            path,
                        )
                    )
    _write_matrix_index(
        run_dir,
        manifest_path=manifest_path,
        task_keys=[spec.key for spec in specs],
        seeds=seeds,
        inference_steps=inference_steps,
        records=records,
    )
    if not jobs:
        return run_dir / "matrix-index.json"

    device = _require_cuda_memory(minimum_free_gib)
    _set_seed(seeds[0])
    model = _build_model(config, device, vae_device)
    first = jobs[0]
    backend = LocalStarWAMBackend(
        model=model,
        config=config,
        context=first[3].unsqueeze(0).to(device=device, dtype=torch.bfloat16),
        context_mask=first[4].unsqueeze(0).to(device=device, dtype=torch.bool),
        stats=_load_stats(),
        preprocessing=first[2],
        device=device,
        runtime_device=(
            f"cuda:0 (physical GPU {physical_gpu_index}, {torch.cuda.get_device_name(device)})"
        ),
        num_inference_steps=first[5],
    )
    adapter = StarWAMAdapter(backend, release=StarWAMRelease())
    try:
        active_task_key: str | None = None
        for (
            spec,
            captured,
            preprocessing,
            context,
            context_mask,
            num_inference_steps,
            seed,
            cache_key,
            path,
        ) in jobs:
            try:
                if active_task_key != spec.key:
                    backend.context = context.unsqueeze(0).to(
                        device=device,
                        dtype=torch.bfloat16,
                    )
                    backend.context_mask = context_mask.unsqueeze(0).to(
                        device=device,
                        dtype=torch.bool,
                    )
                    active_task_key = spec.key
                backend.preprocessing = preprocessing
                backend.num_inference_steps = num_inference_steps
                prediction = adapter.predict_action(captured.observation, seed=seed)
                artifact = ActionPredictionArtifact(
                    observation=captured.observation,
                    prediction=prediction,
                    provenance=_provenance(),
                    preprocessing=preprocessing,
                    inference=_inference_configuration(
                        config,
                        num_inference_steps=num_inference_steps,
                        vae_device=vae_device,
                    ),
                )
                if artifact.cache_key != cache_key:
                    raise RuntimeError("precomputed and generated cache keys differ")
                artifact.write_json(path)
                payload = artifact.to_dict()
                records.append(
                    _matrix_record(
                        spec=spec,
                        seed=seed,
                        num_inference_steps=num_inference_steps,
                        cache_key=cache_key,
                        path=path,
                        payload=payload,
                        status="generated",
                    )
                )
            except Exception as error:
                records.append(
                    {
                        "task_key": spec.key,
                        "task_family": spec.task_family,
                        "context_id": spec.context_id,
                        "seed": seed,
                        "num_inference_steps": num_inference_steps,
                        "cache_key": cache_key,
                        "status": "failed",
                        "error_type": type(error).__name__,
                        "error": str(error),
                    }
                )
            _write_matrix_index(
                run_dir,
                manifest_path=manifest_path,
                task_keys=[task.key for task in specs],
                seeds=seeds,
                inference_steps=inference_steps,
                records=records,
            )
    finally:
        adapter.close()
    failures = sum(record.get("status") == "failed" for record in records)
    if failures:
        raise RuntimeError(f"{failures}/{len(records)} StarWAM matrix predictions failed")
    return run_dir / "matrix-index.json"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mode",
        choices=("observe", "text-cache", "infer", "matrix"),
        default="infer",
    )
    parser.add_argument("--gpu-index", type=int, default=0, help="physical CUDA/EGL GPU")
    parser.add_argument(
        "--run-dir", type=Path, default=REPOSITORY_ROOT / "runs" / "starwam-libero-smoke"
    )
    parser.add_argument("--minimum-free-gib", type=float, default=18.0)
    parser.add_argument("--num-inference-steps", type=int, default=1)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=LIBERO_CF_MANIFEST,
        help="pinned task manifest used by matrix mode",
    )
    parser.add_argument(
        "--task-key",
        action="append",
        default=[],
        help="matrix task key; repeat to select several (default: all)",
    )
    parser.add_argument(
        "--matrix-seed",
        action="append",
        type=int,
        default=[],
        help="matrix diffusion seed; repeat to select several (default: 0,1,2)",
    )
    parser.add_argument(
        "--matrix-inference-steps",
        action="append",
        type=int,
        default=[],
        help="matrix NFE; repeat to select several (default: 1,4,8)",
    )
    parser.add_argument("--vae-device", choices=("cpu", "cuda"), default="cpu")
    parser.add_argument(
        "--verify-large-hashes",
        action="store_true",
        help="rehash the 12 GB checkpoint, 2.8 GB VAE, and 11 GB T5 before running",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    if args.gpu_index < 0:
        raise ValueError("gpu-index must be non-negative")
    if args.minimum_free_gib <= 0:
        raise ValueError("minimum-free-gib must be positive")
    if args.num_inference_steps <= 0:
        raise ValueError("num-inference-steps must be positive")
    matrix_seeds = tuple(args.matrix_seed or (0, 1, 2))
    matrix_inference_steps = tuple(args.matrix_inference_steps or (1, 4, 8))
    if any(seed < 0 for seed in matrix_seeds):
        raise ValueError("matrix seeds must be non-negative")
    if any(steps <= 0 for steps in matrix_inference_steps):
        raise ValueError("matrix inference steps must be positive")
    if len(matrix_seeds) != len(set(matrix_seeds)):
        raise ValueError("matrix seeds must be unique")
    if len(matrix_inference_steps) != len(set(matrix_inference_steps)):
        raise ValueError("matrix inference steps must be unique")
    run_dir = args.run_dir.expanduser().resolve()
    _configure_process(args.gpu_index, run_dir)
    _verify_inputs(verify_large_hashes=args.verify_large_hashes)
    config = _resolved_config(run_dir)

    if args.mode == "matrix":
        index = _run_inference_matrix(
            config,
            run_dir,
            manifest_path=args.manifest.expanduser().resolve(),
            task_keys=args.task_key,
            seeds=matrix_seeds,
            inference_steps=matrix_inference_steps,
            minimum_free_gib=args.minimum_free_gib,
            vae_device="cuda:0" if args.vae_device == "cuda" else "cpu",
            physical_gpu_index=args.gpu_index,
        )
        print(f"wrote matrix index: {index}")
        return

    if args.mode == "text-cache":
        _prepare_text_cache(config, args.minimum_free_gib)
        return
    if args.mode == "observe":
        text_cache_path = _text_cache_path(config)
        if text_cache_path.is_file():
            context, context_mask = _load_text_cache(text_cache_path, config)
            text_cache_hash = _text_condition_sha256(context, context_mask)
        else:
            text_cache_hash = "0" * 64
        captured = _capture_observation()
        _write_observation(captured, _preprocessing(text_cache_hash), run_dir)
        return
    _run_inference(
        config,
        run_dir,
        minimum_free_gib=args.minimum_free_gib,
        num_inference_steps=args.num_inference_steps,
        vae_device="cuda:0" if args.vae_device == "cuda" else "cpu",
        physical_gpu_index=args.gpu_index,
    )


if __name__ == "__main__":
    main()
