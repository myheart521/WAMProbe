import json
import math
from pathlib import Path
from typing import cast

import pytest

from wamprobe.api.counterfactual import (
    ActionBranch,
    CounterfactualValidation,
    RGBFrameReference,
    RobotAction,
    RobotFuture,
    RobotInterventionGroup,
    RobotStateFrame,
    SimulatorSnapshotDescriptor,
)
from wamprobe.counterfactual import CounterfactualArtifact, score_intervention_group


def _snapshot() -> SimulatorSnapshotDescriptor:
    return SimulatorSnapshotDescriptor(
        snapshot_id="libero-spatial-task0-init0-wait30",
        context_id="libero-spatial-task0-init0-wait30",
        simulator="LIBERO/robosuite/MuJoCo",
        simulator_version="libero@8f1084e/robosuite@1.4.0/mujoco@3.9.0",
        state_format="mujoco-mjSTATE_INTEGRATION-float64-v1",
        state_uri="snapshots/integration_state.npy",
        state_sha256="a" * 64,
        state_size_bytes=1024,
        sidecar_uri="snapshots/runtime_state.json",
        sidecar_sha256="b" * 64,
        sidecar_size_bytes=2048,
        timestep=30,
        simulation_time_seconds=1.5,
        restore_policy="libero-integration-and-python-side-state-v1",
    )


def _frame(
    step_index: int,
    *,
    eef_x: float,
    object_x: float,
    reward: float = 0.0,
    success: bool = False,
) -> RobotStateFrame:
    return RobotStateFrame(
        step_index=step_index,
        simulation_time_seconds=1.5 + step_index * 0.05,
        eef_position=(eef_x, 0.0, 1.0),
        eef_axis_angle=(0.0, 0.0, 0.0),
        gripper_qpos=(0.02, -0.02),
        object_state=(object_x, 0.0),
        rgb_frames=(
            RGBFrameReference(
                camera_name="agentview",
                height=2,
                width=2,
                uri=f"images/branch/step-{step_index:03d}-agentview.png",
                sha256=f"{step_index + 1:064x}",
                size_bytes=12,
            ),
        ),
        simulator_state_sha256=f"{step_index + 10:064x}",
        reward=reward,
        success=success,
        done=success,
    )


def _branch(
    branch_id: str,
    action_family: str,
    action_x: float,
    final_eef_x: float,
    final_object_x: float,
    *,
    reward: float = 0.0,
    success: bool = False,
) -> ActionBranch:
    initial = _frame(0, eef_x=0.0, object_x=0.0)
    future = RobotFuture(
        context_id=_snapshot().context_id,
        branch_id=branch_id,
        initial_frame=initial,
        frames=(
            _frame(
                1,
                eef_x=final_eef_x,
                object_x=final_object_x,
                reward=reward,
                success=success,
            ),
        ),
        cumulative_return=reward,
        success=success,
        termination_reason="success" if success else "horizon",
    )
    return ActionBranch(
        branch_id=branch_id,
        action_family=action_family,
        initial_snapshot_sha256=_snapshot().content_sha256,
        action=RobotAction(
            action_space="libero-eef-delta-pose-gripper-v1",
            values=((action_x, 0.0, 0.0, 0.0, 0.0, 0.0, -1.0),),
        ),
        future=future,
    )


def _group() -> RobotInterventionGroup:
    return RobotInterventionGroup(
        context_id=_snapshot().context_id,
        task="pick up the black bowl and place it on the plate",
        snapshot=_snapshot(),
        branches=(
            _branch("noop", "no-op", 0.0, 0.1, 0.0),
            _branch(
                "move-x-positive",
                "directional-positive-x",
                0.5,
                1.0,
                0.5,
                reward=2.0,
                success=True,
            ),
        ),
    )


def _validation() -> CounterfactualValidation:
    return CounterfactualValidation(
        restore_trials=2,
        restored_initial_state_exact=True,
        restored_initial_observation_exact=True,
        repeated_branch_exact=True,
        branch_order_invariant=True,
        max_state_abs_error=0.0,
    )


def test_robot_intervention_group_has_stable_digest_without_raw_payloads() -> None:
    group = _group()

    assert group.content_sha256 == _group().content_sha256
    assert group.horizon == 1
    assert group.action_dim == 7
    payload = group.to_dict()
    snapshot_payload = payload["snapshot"]
    assert isinstance(snapshot_payload, dict)
    assert snapshot_payload["content_sha256"] == group.snapshot.content_sha256
    assert "data" not in json.dumps(payload)


def test_robot_action_rejects_non_finite_or_ragged_values() -> None:
    with pytest.raises(ValueError, match="finite"):
        RobotAction("space", ((math.nan,),))

    with pytest.raises(ValueError, match="same dimension"):
        RobotAction("space", ((0.0, 1.0), (0.0,)))


def test_robot_state_frame_requires_three_dimensional_eef_vectors() -> None:
    with pytest.raises(ValueError, match="must be 3D"):
        RobotStateFrame(
            step_index=0,
            simulation_time_seconds=0.0,
            eef_position=cast(tuple[float, float, float], (0.0, 0.0)),
            eef_axis_angle=(0.0, 0.0, 0.0),
            gripper_qpos=(0.0,),
            object_state=(0.0,),
            rgb_frames=_frame(0, eef_x=0.0, object_x=0.0).rgb_frames,
            simulator_state_sha256="a" * 64,
            reward=0.0,
            success=False,
            done=False,
        )


def test_group_rejects_branches_from_different_snapshots() -> None:
    branch = _branch("noop", "no-op", 0.0, 0.0, 0.0)
    mismatched = ActionBranch(
        branch_id=branch.branch_id,
        action_family=branch.action_family,
        initial_snapshot_sha256="f" * 64,
        action=branch.action,
        future=branch.future,
    )

    with pytest.raises(ValueError, match="snapshot"):
        RobotInterventionGroup(
            context_id=_snapshot().context_id,
            task="task",
            snapshot=_snapshot(),
            branches=(mismatched, _branch("move", "directional", 0.5, 0.5, 0.0)),
        )


def test_group_rejects_mixed_action_shapes_and_initial_frames() -> None:
    first = _branch("noop", "no-op", 0.0, 0.0, 0.0)
    second = _branch("move", "directional", 0.5, 0.5, 0.0)
    mixed_action = ActionBranch(
        branch_id=second.branch_id,
        action_family=second.action_family,
        initial_snapshot_sha256=second.initial_snapshot_sha256,
        action=RobotAction(second.action.action_space, ((0.5, 0.0),)),
        future=second.future,
    )

    with pytest.raises(ValueError, match="action shape"):
        RobotInterventionGroup(
            context_id=_snapshot().context_id,
            task="task",
            snapshot=_snapshot(),
            branches=(first, mixed_action),
        )

    changed_initial = RobotFuture(
        context_id=second.future.context_id,
        branch_id=second.future.branch_id,
        initial_frame=_frame(0, eef_x=0.01, object_x=0.0),
        frames=second.future.frames,
        cumulative_return=second.future.cumulative_return,
        success=second.future.success,
        termination_reason=second.future.termination_reason,
    )
    mixed_initial = ActionBranch(
        branch_id=second.branch_id,
        action_family=second.action_family,
        initial_snapshot_sha256=second.initial_snapshot_sha256,
        action=second.action,
        future=changed_initial,
    )
    with pytest.raises(ValueError, match="initial frame"):
        RobotInterventionGroup(
            context_id=_snapshot().context_id,
            task="task",
            snapshot=_snapshot(),
            branches=(first, mixed_initial),
        )


def test_counterfactual_scores_report_separation_drift_and_return_profile() -> None:
    scores = score_intervention_group(_group())

    assert scores.mean_final_eef_pairwise_distance == pytest.approx(0.9)
    assert scores.mean_final_object_pairwise_distance == pytest.approx(0.5)
    assert scores.noop_final_eef_drift == pytest.approx(0.1)
    assert scores.return_spread == pytest.approx(2.0)
    assert scores.success_rate == pytest.approx(0.5)


def test_counterfactual_artifact_writes_deterministic_json(tmp_path: Path) -> None:
    artifact = CounterfactualArtifact(group=_group(), validation=_validation())
    output = tmp_path / "intervention_group.json"

    artifact.write_json(output)

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "0.1"
    assert payload["artifact_sha256"] == artifact.artifact_sha256
    assert payload["metrics"]["success_rate"] == 0.5
    assert payload["validation"]["branch_order_invariant"] is True
    assert "data" not in json.dumps(payload)
