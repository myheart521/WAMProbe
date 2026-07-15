#!/usr/bin/env python
"""Generate one pinned LIBERO counterfactual intervention group.

This runner needs the isolated StarWAM virtual environment only for its already-pinned
LIBERO, robosuite, MuJoCo, PyTorch, and image dependencies. It does not load a WAM or any
model weights.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
import random
import subprocess
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPOSITORY_ROOT / "src"
LIBERO_ROOT = REPOSITORY_ROOT / "vendor" / "upstream" / "libero"

LIBERO_REVISION = "8f1084e3132a39270c3a13ebe37270a43ece2a01"
TASK_SUITE = "libero_spatial"
TASK_ID = 0
INIT_STATE_INDEX = 0
WAIT_STEPS = 30
SEED = 42
TASK = "pick up the black bowl between the plate and the ramekin and place it on the plate"
CONTEXT_ID = "libero-spatial-task0-init0-wait30"
BDDL_SHA256 = "9b59eb1287802868ad9bc78d58e6d36d4ba31134e679cfdbdf4b0feb660c959b"
INIT_STATES_SHA256 = "cbbc73792ce546c9bec181fd328a411d3183074840b282671dee481511381d0a"
ACTION_SPACE = "libero-eef-delta-pose-gripper-v1"
RESTORE_POLICY = "libero-integration-and-python-side-state-v1"
CAMERAS = (
    ("agentview", "agentview_image"),
    ("wrist", "robot0_eye_in_hand_image"),
)
DUMMY_ACTION = (0.0, 0.0, 0.0, 0.0, 0.0, 0.0, -1.0)
BRANCH_ACTIONS = (
    ("noop", "no-op", DUMMY_ACTION),
    ("move-x-positive", "directional-positive-x", (0.5, 0.0, 0.0, 0.0, 0.0, 0.0, -1.0)),
    ("move-x-negative", "directional-negative-x", (-0.5, 0.0, 0.0, 0.0, 0.0, 0.0, -1.0)),
    ("gripper-close", "gripper-close", (0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0)),
)

if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from wamprobe.api.counterfactual import (  # noqa: E402
    ActionBranch,
    CounterfactualValidation,
    RGBFrameReference,
    RobotAction,
    RobotFuture,
    RobotInterventionGroup,
    RobotStateFrame,
    SimulatorSnapshotDescriptor,
)
from wamprobe.counterfactual import CounterfactualArtifact  # noqa: E402


@dataclass(slots=True)
class RuntimeSnapshot:
    """In-memory state needed to restore one exact branch origin."""

    integration_state: Any
    libero_state: Any
    timestep: int
    simulation_time_seconds: float
    done: bool
    python_rng_state: object
    numpy_rng_state: tuple[Any, ...]
    controller_states: tuple[dict[str, object], ...]
    gripper_actions: tuple[Any, ...]


@dataclass(frozen=True, slots=True)
class TraceStep:
    """Exact comparison data retained only while validating the generator."""

    integration_state: Any
    observation_sha256: str
    reward: float
    success: bool
    done: bool


@dataclass(frozen=True, slots=True)
class BranchTrace:
    """One branch's exact per-step runtime trace."""

    initial_state: Any
    initial_observation_sha256: str
    steps: tuple[TraceStep, ...]


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(8 * 1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def _array_sha256(array: Any) -> str:
    import numpy as np

    contiguous = np.ascontiguousarray(array)
    metadata = json.dumps(
        {"dtype": str(contiguous.dtype), "shape": list(contiguous.shape)},
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    digest = hashlib.sha256(metadata)
    digest.update(contiguous.view(np.uint8).tobytes())
    return digest.hexdigest()


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        temporary.write_text(
            json.dumps(
                payload,
                allow_nan=False,
                indent=2,
                ensure_ascii=False,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def _git_revision(path: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _configure_process(gpu_index: int, run_dir: Path) -> None:
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
    if str(LIBERO_ROOT) not in sys.path:
        sys.path.insert(0, str(LIBERO_ROOT))


def _set_seed(seed: int) -> None:
    import numpy as np

    random.seed(seed)
    np.random.seed(seed)


def _load_init_states(path: Path) -> Any:
    """Load the pinned NumPy array with a minimal PyTorch weights-only allowlist."""

    import numpy as np
    import torch
    from numpy.core.multiarray import _reconstruct  # type: ignore[attr-defined]

    safe_globals = [_reconstruct, np.ndarray, np.dtype, np.dtypes.Float64DType]
    with torch.serialization.safe_globals(safe_globals):
        states = torch.load(path, map_location="cpu", weights_only=True)
    if not isinstance(states, np.ndarray) or states.dtype != np.float64:
        raise TypeError("LIBERO init states must be a float64 NumPy array")
    return states


def _integration_state(environment: Any) -> Any:
    import mujoco
    import numpy as np

    specification = mujoco.mjtState.mjSTATE_INTEGRATION
    state = np.empty(
        mujoco.mj_stateSize(environment.sim.model._model, specification),
        dtype=np.float64,
    )
    mujoco.mj_getState(
        environment.sim.model._model,
        environment.sim.data._data,
        state,
        specification,
    )
    return state


def _set_integration_state(environment: Any, state: Any) -> None:
    import mujoco

    mujoco.mj_setState(
        environment.sim.model._model,
        environment.sim.data._data,
        state,
        mujoco.mjtState.mjSTATE_INTEGRATION,
    )


def _copy_controller_state(controller: Any) -> dict[str, object]:
    """Copy mutable controller values while preserving its simulator reference."""

    import numpy as np

    state: dict[str, object] = {}
    for name, value in vars(controller).items():
        if name == "sim":
            continue
        if isinstance(value, np.ndarray):
            state[name] = value.copy()
        elif isinstance(value, (bool, int, float, str)) or value is None:
            state[name] = value
    return state


def _restore_controller_state(controller: Any, state: dict[str, object]) -> None:
    import numpy as np

    for name, value in state.items():
        restored = value.copy() if isinstance(value, np.ndarray) else value
        setattr(controller, name, restored)


def _json_value(value: object) -> object:
    import numpy as np

    if isinstance(value, np.ndarray):
        return {
            "dtype": str(value.dtype),
            "shape": list(value.shape),
            "values": value.tolist(),
        }
    if isinstance(value, np.generic):
        return value.item()
    return value


def _numpy_rng_payload(state: tuple[Any, ...]) -> dict[str, object]:
    return {
        "bit_generator": str(state[0]),
        "keys": [int(value) for value in state[1]],
        "position": int(state[2]),
        "has_gauss": int(state[3]),
        "cached_gaussian": float(state[4]),
    }


def _runtime_sidecar(snapshot: RuntimeSnapshot, state_uri: str) -> dict[str, object]:
    return {
        "schema_version": "0.1",
        "context_id": CONTEXT_ID,
        "state_uri": state_uri,
        "libero_wrapper_state": [float(value) for value in snapshot.libero_state],
        "timestep": snapshot.timestep,
        "simulation_time_seconds": snapshot.simulation_time_seconds,
        "done": snapshot.done,
        "python_rng_state": snapshot.python_rng_state,
        "numpy_rng_state": _numpy_rng_payload(snapshot.numpy_rng_state),
        "controllers": [
            {name: _json_value(value) for name, value in state.items()}
            for state in snapshot.controller_states
        ],
        "gripper_current_actions": [action.tolist() for action in snapshot.gripper_actions],
        "restore_policy": {
            "mujoco": "mjSTATE_INTEGRATION",
            "controller": "restore copied mutable controller values",
            "gripper": "restore GripperModel.current_action",
            "observables": "clear cache, reset observables, force one update",
            "observation_semantics": (
                "canonical observation is force-refreshed from the restored end-of-control state; "
                "it is not the potentially earlier camera sample returned by the preceding step"
            ),
            "clock": "restore timestep, cur_time, and done",
            "rng": "restore Python and NumPy global RNG states before observable reset",
        },
    }


def _capture_runtime_snapshot(environment: Any) -> RuntimeSnapshot:
    import numpy as np

    return RuntimeSnapshot(
        integration_state=_integration_state(environment).copy(),
        libero_state=np.asarray(environment.get_sim_state(), dtype=np.float64).copy(),
        timestep=int(environment.env.timestep),
        simulation_time_seconds=float(environment.env.cur_time),
        done=bool(environment.env.done),
        python_rng_state=random.getstate(),
        numpy_rng_state=copy.deepcopy(np.random.get_state()),
        controller_states=tuple(
            _copy_controller_state(robot.controller) for robot in environment.robots
        ),
        gripper_actions=tuple(
            np.asarray(robot.gripper.current_action, dtype=np.float64).copy()
            for robot in environment.robots
        ),
    )


def _restore_runtime_snapshot(environment: Any, snapshot: RuntimeSnapshot) -> Any:
    import numpy as np

    random.setstate(snapshot.python_rng_state)
    np.random.set_state(snapshot.numpy_rng_state)
    _set_integration_state(environment, snapshot.integration_state)
    environment.env.timestep = snapshot.timestep
    environment.env.cur_time = snapshot.simulation_time_seconds
    environment.env.done = snapshot.done
    environment.sim.forward()
    environment._post_process()

    for robot, controller_state, gripper_action in zip(
        environment.robots,
        snapshot.controller_states,
        snapshot.gripper_actions,
        strict=True,
    ):
        _restore_controller_state(robot.controller, controller_state)
        robot.gripper.current_action = gripper_action.copy()

    environment.env._obs_cache = {}
    for observable in environment.env._observables.values():
        observable.reset()
    environment._update_observables(force=True)
    observation = environment.env._get_observations()

    # forward() is required to refresh derived quantities, but it can change solver
    # warm-start values. Restore the complete integration vector once more without a
    # second forward so the branch begins byte-identically to the recorded snapshot.
    _set_integration_state(environment, snapshot.integration_state)
    return observation


def _quat_to_axis_angle(quaternion: Any) -> Any:
    import numpy as np

    quat = np.asarray(quaternion, dtype=np.float64).copy()
    quat[3] = np.clip(quat[3], -1.0, 1.0)
    denominator = math.sqrt(max(0.0, 1.0 - float(quat[3]) ** 2))
    if math.isclose(denominator, 0.0):
        return np.zeros(3, dtype=np.float64)
    angle = 2.0 * math.acos(float(quat[3]))
    return quat[:3] * angle / denominator


def _observation_sha256(observation: Any) -> str:
    payload = {
        key: _array_sha256(observation[key])
        for key in (
            "agentview_image",
            "robot0_eye_in_hand_image",
            "robot0_eef_pos",
            "robot0_eef_quat",
            "robot0_gripper_qpos",
            "object-state",
        )
    }
    return hashlib.sha256(
        json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    ).hexdigest()


def _write_rgb_references(
    observation: Any,
    *,
    run_dir: Path,
    relative_directory: Path,
    step_index: int,
) -> tuple[RGBFrameReference, ...]:
    import numpy as np
    from PIL import Image

    references: list[RGBFrameReference] = []
    for camera_name, observation_key in CAMERAS:
        image = np.ascontiguousarray(observation[observation_key], dtype=np.uint8)
        height, width, channels = image.shape
        if channels != 3:
            raise RuntimeError(f"{camera_name} returned a non-RGB image: {image.shape}")
        path = run_dir / relative_directory / f"step-{step_index:03d}-{camera_name}.png"
        path.parent.mkdir(parents=True, exist_ok=True)
        Image.fromarray(image).save(path)
        references.append(
            RGBFrameReference(
                camera_name=camera_name,
                height=int(height),
                width=int(width),
                uri=path.relative_to(run_dir).as_posix(),
                sha256=_sha256_file(path),
                size_bytes=path.stat().st_size,
            )
        )
    return tuple(references)


def _typed_frame(
    environment: Any,
    observation: Any,
    *,
    run_dir: Path,
    relative_directory: Path,
    step_index: int,
    reward: float,
    success: bool,
    done: bool,
) -> RobotStateFrame:
    return RobotStateFrame(
        step_index=step_index,
        simulation_time_seconds=float(environment.env.cur_time),
        eef_position=tuple(float(value) for value in observation["robot0_eef_pos"]),
        eef_axis_angle=tuple(
            float(value) for value in _quat_to_axis_angle(observation["robot0_eef_quat"])
        ),
        gripper_qpos=tuple(float(value) for value in observation["robot0_gripper_qpos"]),
        object_state=tuple(float(value) for value in observation["object-state"]),
        rgb_frames=_write_rgb_references(
            observation,
            run_dir=run_dir,
            relative_directory=relative_directory,
            step_index=step_index,
        ),
        simulator_state_sha256=_array_sha256(_integration_state(environment)),
        reward=float(reward),
        success=bool(success),
        done=bool(done),
    )


def _trace_step(
    environment: Any,
    observation: Any,
    *,
    reward: float,
    success: bool,
    done: bool,
) -> TraceStep:
    return TraceStep(
        integration_state=_integration_state(environment).copy(),
        observation_sha256=_observation_sha256(observation),
        reward=float(reward),
        success=bool(success),
        done=bool(done),
    )


def _rollout(
    environment: Any,
    snapshot: RuntimeSnapshot,
    *,
    branch_id: str,
    action: tuple[float, ...],
    horizon: int,
    persist: bool,
    run_dir: Path,
    initial_frame: RobotStateFrame,
) -> tuple[RobotFuture | None, BranchTrace]:
    import numpy as np

    initial_observation = _restore_runtime_snapshot(environment, snapshot)
    initial_state = _integration_state(environment).copy()
    typed_frames: list[RobotStateFrame] = []
    trace_steps: list[TraceStep] = []
    cumulative_return = 0.0
    succeeded = False
    last_done = False
    action_array = np.asarray(action, dtype=np.float64)

    for step_index in range(1, horizon + 1):
        observation, reward, last_done, _ = environment.step(action_array)
        success = bool(environment.check_success())
        succeeded = succeeded or success
        cumulative_return += float(reward)
        trace_steps.append(
            _trace_step(
                environment,
                observation,
                reward=float(reward),
                success=success,
                done=bool(last_done),
            )
        )
        if persist:
            typed_frames.append(
                _typed_frame(
                    environment,
                    observation,
                    run_dir=run_dir,
                    relative_directory=Path("images") / branch_id,
                    step_index=step_index,
                    reward=float(reward),
                    success=success,
                    done=bool(last_done),
                )
            )

    future = (
        RobotFuture(
            context_id=CONTEXT_ID,
            branch_id=branch_id,
            initial_frame=initial_frame,
            frames=tuple(typed_frames),
            cumulative_return=cumulative_return,
            success=succeeded,
            termination_reason="success" if succeeded else "horizon",
        )
        if persist
        else None
    )
    trace = BranchTrace(
        initial_state=initial_state,
        initial_observation_sha256=_observation_sha256(initial_observation),
        steps=tuple(trace_steps),
    )
    return future, trace


def _trace_exact(left: BranchTrace, right: BranchTrace) -> bool:
    import numpy as np

    return (
        np.array_equal(left.initial_state, right.initial_state)
        and left.initial_observation_sha256 == right.initial_observation_sha256
        and len(left.steps) == len(right.steps)
        and all(
            np.array_equal(left_step.integration_state, right_step.integration_state)
            and left_step.observation_sha256 == right_step.observation_sha256
            and left_step.reward == right_step.reward
            and left_step.success == right_step.success
            and left_step.done == right_step.done
            for left_step, right_step in zip(left.steps, right.steps, strict=True)
        )
    )


def _max_state_error(comparisons: list[tuple[BranchTrace, BranchTrace]]) -> float:
    import numpy as np

    errors: list[float] = []
    for left, right in comparisons:
        errors.append(float(np.max(np.abs(left.initial_state - right.initial_state))))
        errors.extend(
            float(np.max(np.abs(left_step.integration_state - right_step.integration_state)))
            for left_step, right_step in zip(left.steps, right.steps, strict=True)
        )
    return max(errors, default=0.0)


def _snapshot_descriptor(
    snapshot: RuntimeSnapshot,
    *,
    run_dir: Path,
    simulator_version: str,
) -> SimulatorSnapshotDescriptor:
    import numpy as np

    state_path = run_dir / "snapshots" / "integration_state.npy"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    with state_path.open("wb") as stream:
        np.save(stream, snapshot.integration_state, allow_pickle=False)

    sidecar_path = run_dir / "snapshots" / "runtime_state.json"
    _write_json(
        sidecar_path,
        _runtime_sidecar(snapshot, state_path.relative_to(run_dir).as_posix()),
    )
    return SimulatorSnapshotDescriptor(
        snapshot_id=CONTEXT_ID,
        context_id=CONTEXT_ID,
        simulator="LIBERO/robosuite/MuJoCo",
        simulator_version=simulator_version,
        state_format="numpy-npy-mujoco-mjSTATE_INTEGRATION-float64-v1",
        state_uri=state_path.relative_to(run_dir).as_posix(),
        state_sha256=_sha256_file(state_path),
        state_size_bytes=state_path.stat().st_size,
        sidecar_uri=sidecar_path.relative_to(run_dir).as_posix(),
        sidecar_sha256=_sha256_file(sidecar_path),
        sidecar_size_bytes=sidecar_path.stat().st_size,
        timestep=snapshot.timestep,
        simulation_time_seconds=snapshot.simulation_time_seconds,
        restore_policy=RESTORE_POLICY,
    )


def _prepare_environment(run_dir: Path) -> tuple[Any, Any, str]:
    import mujoco
    import robosuite
    from libero.libero import benchmark, get_libero_path
    from libero.libero.envs import OffScreenRenderEnv

    revision = _git_revision(LIBERO_ROOT)
    if revision != LIBERO_REVISION:
        raise RuntimeError(f"LIBERO revision mismatch: expected {LIBERO_REVISION}, got {revision}")
    suite = benchmark.get_benchmark_dict()[TASK_SUITE]()
    task = suite.get_task(TASK_ID)
    if task.language != TASK:
        raise RuntimeError(f"pinned LIBERO task changed: expected {TASK!r}, got {task.language!r}")
    bddl_path = Path(suite.get_task_bddl_file_path(TASK_ID))
    init_states_path = (
        Path(get_libero_path("init_states")) / task.problem_folder / task.init_states_file
    )
    if _sha256_file(bddl_path) != BDDL_SHA256:
        raise RuntimeError("LIBERO BDDL hash mismatch")
    if _sha256_file(init_states_path) != INIT_STATES_SHA256:
        raise RuntimeError("LIBERO init-state hash mismatch")
    init_states = _load_init_states(init_states_path)
    if init_states.shape != (50, 92):
        raise RuntimeError(f"unexpected LIBERO init-state shape: {init_states.shape}")

    environment = OffScreenRenderEnv(
        bddl_file_name=str(bddl_path),
        camera_heights=256,
        camera_widths=256,
    )
    environment.seed(SEED)
    version = f"libero@{revision}/robosuite@{robosuite.__version__}/mujoco@{mujoco.__version__}"
    _write_json(
        run_dir / "benchmark_provenance.json",
        {
            "libero_revision": revision,
            "robosuite_version": robosuite.__version__,
            "mujoco_version": mujoco.__version__,
            "task_suite": TASK_SUITE,
            "task_id": TASK_ID,
            "task": TASK,
            "init_state_index": INIT_STATE_INDEX,
            "wait_steps": WAIT_STEPS,
            "seed": SEED,
            "bddl_uri": str(bddl_path),
            "bddl_sha256": BDDL_SHA256,
            "init_states_uri": str(init_states_path),
            "init_states_sha256": INIT_STATES_SHA256,
            "init_states_shape": list(init_states.shape),
            "action_space": ACTION_SPACE,
            "control_frequency_hz": environment.env.control_freq,
            "control_timestep_seconds": environment.env.control_timestep,
            "snapshot_observation_semantics": (
                "compare independent force-refreshed observations after restore; robosuite step() "
                "camera samples can precede the end-of-control state"
            ),
        },
    )
    return environment, init_states, version


def _generate(run_dir: Path, horizon: int) -> CounterfactualArtifact:
    import numpy as np

    environment, init_states, simulator_version = _prepare_environment(run_dir)
    try:
        environment.reset()
        observation = environment.set_init_state(init_states[INIT_STATE_INDEX])
        for _ in range(WAIT_STEPS):
            observation, _, _, _ = environment.step(DUMMY_ACTION)

        snapshot = _capture_runtime_snapshot(environment)
        descriptor = _snapshot_descriptor(
            snapshot,
            run_dir=run_dir,
            simulator_version=simulator_version,
        )
        original_state = snapshot.integration_state.copy()

        restored_observation = _restore_runtime_snapshot(environment, snapshot)
        restored_state = _integration_state(environment).copy()
        initial_frame = _typed_frame(
            environment,
            restored_observation,
            run_dir=run_dir,
            relative_directory=Path("images") / "initial",
            step_index=0,
            reward=0.0,
            success=bool(environment.check_success()),
            done=bool(environment.env.done),
        )
        verification_observation = _restore_runtime_snapshot(environment, snapshot)
        verification_state = _integration_state(environment).copy()

        branches: list[ActionBranch] = []
        primary_traces: dict[str, BranchTrace] = {}
        for branch_id, action_family, action in BRANCH_ACTIONS:
            future, trace = _rollout(
                environment,
                snapshot,
                branch_id=branch_id,
                action=action,
                horizon=horizon,
                persist=True,
                run_dir=run_dir,
                initial_frame=initial_frame,
            )
            if future is None:
                raise AssertionError("persisted rollout did not return a future")
            branch = ActionBranch(
                branch_id=branch_id,
                action_family=action_family,
                initial_snapshot_sha256=descriptor.content_sha256,
                action=RobotAction(
                    action_space=ACTION_SPACE,
                    values=tuple(action for _ in range(horizon)),
                ),
                future=future,
            )
            branches.append(branch)
            primary_traces[branch_id] = trace
            _write_json(run_dir / "branches" / f"{branch_id}.json", branch.to_dict())

        reverse_traces: dict[str, BranchTrace] = {}
        for branch_id, _, action in reversed(BRANCH_ACTIONS):
            _, trace = _rollout(
                environment,
                snapshot,
                branch_id=branch_id,
                action=action,
                horizon=horizon,
                persist=False,
                run_dir=run_dir,
                initial_frame=initial_frame,
            )
            reverse_traces[branch_id] = trace

        _, repeated_trace = _rollout(
            environment,
            snapshot,
            branch_id="noop",
            action=DUMMY_ACTION,
            horizon=horizon,
            persist=False,
            run_dir=run_dir,
            initial_frame=initial_frame,
        )
        order_comparisons = [
            (primary_traces[branch_id], reverse_traces[branch_id])
            for branch_id, _, _ in BRANCH_ACTIONS
        ]
        repeat_comparison = (primary_traces["noop"], repeated_trace)
        restore_state_error = max(
            float(np.max(np.abs(original_state - restored_state))),
            float(np.max(np.abs(original_state - verification_state))),
        )
        validation = CounterfactualValidation(
            restore_trials=2,
            restored_initial_state_exact=bool(
                np.array_equal(original_state, restored_state)
                and np.array_equal(original_state, verification_state)
            ),
            restored_initial_observation_exact=(
                _observation_sha256(restored_observation)
                == _observation_sha256(verification_observation)
            ),
            repeated_branch_exact=_trace_exact(*repeat_comparison),
            branch_order_invariant=all(_trace_exact(*pair) for pair in order_comparisons),
            max_state_abs_error=max(
                restore_state_error,
                _max_state_error([*order_comparisons, repeat_comparison]),
            ),
        )
        group = RobotInterventionGroup(
            context_id=CONTEXT_ID,
            task=TASK,
            snapshot=descriptor,
            branches=tuple(branches),
        )
        artifact = CounterfactualArtifact(group=group, validation=validation)
        artifact.write_json(run_dir / "intervention_group.json")
        _write_json(run_dir / "validation.json", validation.to_dict())
        if not validation.passed:
            raise RuntimeError(
                f"counterfactual restore validation failed; inspect {run_dir / 'validation.json'}"
            )
        return artifact
    finally:
        environment.close()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gpu-index", type=int, default=0, help="physical EGL GPU index")
    parser.add_argument(
        "--run-dir",
        type=Path,
        default=REPOSITORY_ROOT / "runs" / "libero-cf-pilot",
    )
    parser.add_argument("--horizon", type=int, default=8, help="control steps per action branch")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    if args.gpu_index < 0:
        raise ValueError("gpu-index must be non-negative")
    if args.horizon <= 0:
        raise ValueError("horizon must be positive")
    run_dir = args.run_dir.expanduser().resolve()
    _configure_process(args.gpu_index, run_dir)
    _set_seed(SEED)
    artifact = _generate(run_dir, args.horizon)
    print(
        json.dumps(
            {
                "artifact": str(run_dir / "intervention_group.json"),
                "artifact_sha256": artifact.artifact_sha256,
                "group_sha256": artifact.group.content_sha256,
                "snapshot_sha256": artifact.group.snapshot.content_sha256,
                "branches": len(artifact.group.branches),
                "horizon": artifact.group.horizon,
                "metrics": artifact.metrics.to_dict(),
                "validation": artifact.validation.to_dict(),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
