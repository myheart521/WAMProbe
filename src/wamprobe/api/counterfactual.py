"""Dependency-free contracts for paired robot counterfactual rollouts."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass


def _require_non_empty(value: str, field_name: str) -> None:
    if not value.strip():
        raise ValueError(f"{field_name} must not be empty")


def _validate_sha256(value: str, field_name: str) -> None:
    if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
        raise ValueError(f"{field_name} must be a lowercase 64-character SHA256 digest")


def _stable_sha256(payload: dict[str, object]) -> str:
    encoded = json.dumps(
        payload,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _all_finite(values: tuple[float, ...]) -> bool:
    return all(math.isfinite(value) for value in values)


@dataclass(frozen=True, slots=True)
class SimulatorSnapshotDescriptor:
    """Content-addressed simulator snapshot without embedding its large payloads."""

    snapshot_id: str
    context_id: str
    simulator: str
    simulator_version: str
    state_format: str
    state_uri: str
    state_sha256: str
    state_size_bytes: int
    sidecar_uri: str
    sidecar_sha256: str
    sidecar_size_bytes: int
    timestep: int
    simulation_time_seconds: float
    restore_policy: str

    def __post_init__(self) -> None:
        for value, field_name in (
            (self.snapshot_id, "snapshot_id"),
            (self.context_id, "snapshot context_id"),
            (self.simulator, "simulator"),
            (self.simulator_version, "simulator_version"),
            (self.state_format, "state_format"),
            (self.state_uri, "state_uri"),
            (self.sidecar_uri, "sidecar_uri"),
            (self.restore_policy, "restore_policy"),
        ):
            _require_non_empty(value, field_name)
        _validate_sha256(self.state_sha256, "state_sha256")
        _validate_sha256(self.sidecar_sha256, "sidecar_sha256")
        if self.state_size_bytes <= 0 or self.sidecar_size_bytes <= 0:
            raise ValueError("snapshot payload sizes must be positive")
        if (
            isinstance(self.timestep, bool)
            or not isinstance(self.timestep, int)
            or self.timestep < 0
        ):
            raise ValueError("snapshot timestep must be a non-negative integer")
        if not math.isfinite(self.simulation_time_seconds) or self.simulation_time_seconds < 0:
            raise ValueError("snapshot simulation time must be finite and non-negative")

    def _payload(self) -> dict[str, object]:
        return {
            "snapshot_id": self.snapshot_id,
            "context_id": self.context_id,
            "simulator": self.simulator,
            "simulator_version": self.simulator_version,
            "state_format": self.state_format,
            "state_uri": self.state_uri,
            "state_sha256": self.state_sha256,
            "state_size_bytes": self.state_size_bytes,
            "sidecar_uri": self.sidecar_uri,
            "sidecar_sha256": self.sidecar_sha256,
            "sidecar_size_bytes": self.sidecar_size_bytes,
            "timestep": self.timestep,
            "simulation_time_seconds": self.simulation_time_seconds,
            "restore_policy": self.restore_policy,
        }

    @property
    def content_sha256(self) -> str:
        """Return a semantic digest over the complete restore contract."""

        return _stable_sha256(self._payload())

    def to_dict(self) -> dict[str, object]:
        """Return the JSON descriptor and its semantic digest."""

        return {**self._payload(), "content_sha256": self.content_sha256}


@dataclass(frozen=True, slots=True)
class RGBFrameReference:
    """Reference to one encoded RGB frame stored outside the JSON contract."""

    camera_name: str
    height: int
    width: int
    uri: str
    sha256: str
    size_bytes: int

    def __post_init__(self) -> None:
        _require_non_empty(self.camera_name, "camera_name")
        _require_non_empty(self.uri, "RGB frame URI")
        _validate_sha256(self.sha256, "RGB frame sha256")
        if self.height <= 0 or self.width <= 0:
            raise ValueError("RGB frame dimensions must be positive")
        if self.size_bytes <= 0:
            raise ValueError("RGB frame size must be positive")

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-compatible external frame reference."""

        return {
            "camera_name": self.camera_name,
            "shape": [self.height, self.width, 3],
            "encoding": "png",
            "uri": self.uri,
            "sha256": self.sha256,
            "size_bytes": self.size_bytes,
        }


@dataclass(frozen=True, slots=True)
class RobotAction:
    """A typed robot action sequence in one explicitly named action space."""

    action_space: str
    values: tuple[tuple[float, ...], ...]

    def __post_init__(self) -> None:
        _require_non_empty(self.action_space, "action_space")
        if not self.values or not self.values[0]:
            raise ValueError("robot action must contain a non-empty sequence")
        action_dim = len(self.values[0])
        if any(len(action) != action_dim for action in self.values):
            raise ValueError("all robot actions must have the same dimension")
        if any(not math.isfinite(value) for action in self.values for value in action):
            raise ValueError("robot action values must be finite")

    @property
    def horizon(self) -> int:
        """Return the number of control steps."""

        return len(self.values)

    @property
    def action_dim(self) -> int:
        """Return the action-vector width."""

        return len(self.values[0])

    @property
    def content_sha256(self) -> str:
        """Return a stable digest over action semantics and values."""

        return _stable_sha256(self.to_dict())

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-compatible action sequence."""

        return {
            "action_space": self.action_space,
            "values": [list(action) for action in self.values],
            "horizon": self.horizon,
            "action_dim": self.action_dim,
        }


@dataclass(frozen=True, slots=True)
class RobotStateFrame:
    """One lightweight simulator state and image-reference record."""

    step_index: int
    simulation_time_seconds: float
    eef_position: tuple[float, float, float]
    eef_axis_angle: tuple[float, float, float]
    gripper_qpos: tuple[float, ...]
    object_state: tuple[float, ...]
    rgb_frames: tuple[RGBFrameReference, ...]
    simulator_state_sha256: str
    reward: float
    success: bool
    done: bool

    def __post_init__(self) -> None:
        if (
            isinstance(self.step_index, bool)
            or not isinstance(self.step_index, int)
            or self.step_index < 0
        ):
            raise ValueError("step_index must be a non-negative integer")
        if not math.isfinite(self.simulation_time_seconds) or self.simulation_time_seconds < 0:
            raise ValueError("frame simulation time must be finite and non-negative")
        if len(self.eef_position) != 3 or len(self.eef_axis_angle) != 3:
            raise ValueError("end-effector position and axis-angle vectors must be 3D")
        if not self.gripper_qpos or not self.object_state:
            raise ValueError("gripper and object state vectors must not be empty")
        state_values = (
            *self.eef_position,
            *self.eef_axis_angle,
            *self.gripper_qpos,
            *self.object_state,
        )
        if not _all_finite(state_values):
            raise ValueError("robot state values must be finite")
        if not self.rgb_frames:
            raise ValueError("robot state frame requires at least one RGB reference")
        camera_names = [frame.camera_name for frame in self.rgb_frames]
        if len(camera_names) != len(set(camera_names)):
            raise ValueError("RGB camera names must be unique within a state frame")
        _validate_sha256(self.simulator_state_sha256, "simulator_state_sha256")
        if not math.isfinite(self.reward):
            raise ValueError("frame reward must be finite")
        if not isinstance(self.success, bool) or not isinstance(self.done, bool):
            raise ValueError("frame success and done values must be booleans")

    @property
    def content_sha256(self) -> str:
        """Return a stable digest without loading referenced PNG bytes."""

        return _stable_sha256(self.to_dict())

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-compatible state descriptor."""

        return {
            "step_index": self.step_index,
            "simulation_time_seconds": self.simulation_time_seconds,
            "eef_position": list(self.eef_position),
            "eef_axis_angle": list(self.eef_axis_angle),
            "gripper_qpos": list(self.gripper_qpos),
            "object_state": list(self.object_state),
            "rgb_frames": [frame.to_dict() for frame in self.rgb_frames],
            "simulator_state_sha256": self.simulator_state_sha256,
            "reward": self.reward,
            "success": self.success,
            "done": self.done,
        }


@dataclass(frozen=True, slots=True)
class RobotFuture:
    """Ground-truth state future for one branch from a recorded initial frame."""

    context_id: str
    branch_id: str
    initial_frame: RobotStateFrame
    frames: tuple[RobotStateFrame, ...]
    cumulative_return: float
    success: bool
    termination_reason: str

    def __post_init__(self) -> None:
        _require_non_empty(self.context_id, "future context_id")
        _require_non_empty(self.branch_id, "future branch_id")
        _require_non_empty(self.termination_reason, "termination_reason")
        if self.initial_frame.step_index != 0:
            raise ValueError("future initial frame must use step_index 0")
        if not self.frames:
            raise ValueError("robot future must contain at least one post-action frame")
        expected_indices = tuple(range(1, len(self.frames) + 1))
        if tuple(frame.step_index for frame in self.frames) != expected_indices:
            raise ValueError("future frame step indices must be contiguous and start at 1")
        if not math.isfinite(self.cumulative_return):
            raise ValueError("cumulative_return must be finite")
        observed_return = sum(frame.reward for frame in self.frames)
        if not math.isclose(self.cumulative_return, observed_return, abs_tol=1e-12):
            raise ValueError("cumulative_return must equal the sum of frame rewards")
        if not isinstance(self.success, bool):
            raise ValueError("future success must be a boolean")
        if self.success != any(frame.success for frame in self.frames):
            raise ValueError("future success must match its state frames")

        expected_object_dim = len(self.initial_frame.object_state)
        expected_gripper_dim = len(self.initial_frame.gripper_qpos)
        expected_cameras = tuple(
            (frame.camera_name, frame.height, frame.width)
            for frame in self.initial_frame.rgb_frames
        )
        for frame in self.frames:
            if len(frame.object_state) != expected_object_dim:
                raise ValueError("future object-state dimensions must remain constant")
            if len(frame.gripper_qpos) != expected_gripper_dim:
                raise ValueError("future gripper-state dimensions must remain constant")
            cameras = tuple(
                (camera.camera_name, camera.height, camera.width) for camera in frame.rgb_frames
            )
            if cameras != expected_cameras:
                raise ValueError("future camera order and dimensions must remain constant")

    @property
    def horizon(self) -> int:
        """Return the number of post-intervention state frames."""

        return len(self.frames)

    @property
    def final_frame(self) -> RobotStateFrame:
        """Return the last observed state."""

        return self.frames[-1]

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-compatible future descriptor."""

        return {
            "context_id": self.context_id,
            "branch_id": self.branch_id,
            "initial_frame": self.initial_frame.to_dict(),
            "frames": [frame.to_dict() for frame in self.frames],
            "horizon": self.horizon,
            "cumulative_return": self.cumulative_return,
            "success": self.success,
            "termination_reason": self.termination_reason,
        }


@dataclass(frozen=True, slots=True)
class ActionBranch:
    """One named action intervention and its simulator ground-truth future."""

    branch_id: str
    action_family: str
    initial_snapshot_sha256: str
    action: RobotAction
    future: RobotFuture

    def __post_init__(self) -> None:
        _require_non_empty(self.branch_id, "branch_id")
        _require_non_empty(self.action_family, "action_family")
        _validate_sha256(self.initial_snapshot_sha256, "initial_snapshot_sha256")
        if self.future.branch_id != self.branch_id:
            raise ValueError("action branch and future branch_id values must match")
        if self.action.horizon != self.future.horizon:
            raise ValueError("action and future horizons must match")

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-compatible paired branch."""

        return {
            "branch_id": self.branch_id,
            "action_family": self.action_family,
            "initial_snapshot_sha256": self.initial_snapshot_sha256,
            "action": self.action.to_dict(),
            "future": self.future.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class RobotInterventionGroup:
    """At least two action branches restored from one identical simulator snapshot."""

    context_id: str
    task: str
    snapshot: SimulatorSnapshotDescriptor
    branches: tuple[ActionBranch, ...]

    def __post_init__(self) -> None:
        _require_non_empty(self.context_id, "intervention context_id")
        _require_non_empty(self.task, "intervention task")
        if len(self.branches) < 2:
            raise ValueError("robot intervention group requires at least two branches")
        if self.snapshot.context_id != self.context_id:
            raise ValueError("snapshot and intervention context_id values must match")

        branch_ids = [branch.branch_id for branch in self.branches]
        action_families = [branch.action_family for branch in self.branches]
        if len(branch_ids) != len(set(branch_ids)):
            raise ValueError("branch_id values must be unique within an intervention group")
        if len(action_families) != len(set(action_families)):
            raise ValueError("action_family values must be unique within an intervention group")
        if any(branch.future.context_id != self.context_id for branch in self.branches):
            raise ValueError("branch future context_id values must match the intervention")
        if any(
            branch.initial_snapshot_sha256 != self.snapshot.content_sha256
            for branch in self.branches
        ):
            raise ValueError("all branches must reference the same semantic snapshot")

        action_shapes = {
            (branch.action.horizon, branch.action.action_dim) for branch in self.branches
        }
        if len(action_shapes) != 1:
            raise ValueError("all branch action shapes must match")
        action_spaces = {branch.action.action_space for branch in self.branches}
        if len(action_spaces) != 1:
            raise ValueError("all branches must use the same action_space")
        initial_hashes = {branch.future.initial_frame.content_sha256 for branch in self.branches}
        if len(initial_hashes) != 1:
            raise ValueError("all branches must share an identical initial frame")

    @property
    def horizon(self) -> int:
        """Return the common branch horizon."""

        return self.branches[0].action.horizon

    @property
    def action_dim(self) -> int:
        """Return the common action-vector width."""

        return self.branches[0].action.action_dim

    @property
    def action_space(self) -> str:
        """Return the common semantic action-space identifier."""

        return self.branches[0].action.action_space

    @property
    def content_sha256(self) -> str:
        """Return a stable digest over the complete lightweight intervention group."""

        return _stable_sha256(self.to_dict())

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-compatible intervention group without raw state or RGB bytes."""

        return {
            "context_id": self.context_id,
            "task": self.task,
            "snapshot": self.snapshot.to_dict(),
            "action_space": self.action_space,
            "horizon": self.horizon,
            "action_dim": self.action_dim,
            "branches": [branch.to_dict() for branch in self.branches],
        }


@dataclass(frozen=True, slots=True)
class CounterfactualValidation:
    """Measured restore and branch-order reproducibility checks."""

    restore_trials: int
    restored_initial_state_exact: bool
    restored_initial_observation_exact: bool
    repeated_branch_exact: bool
    branch_order_invariant: bool
    max_state_abs_error: float

    def __post_init__(self) -> None:
        if (
            isinstance(self.restore_trials, bool)
            or not isinstance(self.restore_trials, int)
            or self.restore_trials < 2
        ):
            raise ValueError("restore_trials must be an integer of at least two")
        exactness = (
            self.restored_initial_state_exact,
            self.restored_initial_observation_exact,
            self.repeated_branch_exact,
            self.branch_order_invariant,
        )
        if any(not isinstance(value, bool) for value in exactness):
            raise ValueError("counterfactual exactness checks must be booleans")
        if not math.isfinite(self.max_state_abs_error) or self.max_state_abs_error < 0:
            raise ValueError("max_state_abs_error must be finite and non-negative")

    @property
    def passed(self) -> bool:
        """Return whether all exact restore checks passed."""

        return (
            self.restored_initial_state_exact
            and self.restored_initial_observation_exact
            and self.repeated_branch_exact
            and self.branch_order_invariant
            and self.max_state_abs_error == 0.0
        )

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-compatible validation record."""

        return {
            "restore_trials": self.restore_trials,
            "restored_initial_state_exact": self.restored_initial_state_exact,
            "restored_initial_observation_exact": self.restored_initial_observation_exact,
            "repeated_branch_exact": self.repeated_branch_exact,
            "branch_order_invariant": self.branch_order_invariant,
            "max_state_abs_error": self.max_state_abs_error,
            "passed": self.passed,
        }
