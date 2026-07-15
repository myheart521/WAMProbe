import math

import pytest

from wamprobe.api.robotics import ActionPrediction, InferenceRuntime, RGBFrame, RobotObservation


def _observation() -> RobotObservation:
    return RobotObservation(
        context_id="libero-spatial-task0-init0-wait30",
        task="pick up the black bowl and place it on the plate",
        frames=(
            RGBFrame("agentview", height=2, width=2, data=bytes(range(12))),
            RGBFrame("wrist", height=2, width=2, data=bytes(reversed(range(12)))),
        ),
        proprio=(0.1, 0.2, 0.3),
        proprio_fields=("eef_x", "eef_y", "eef_z"),
    )


def test_robot_observation_has_stable_content_digest() -> None:
    first = _observation()
    second = _observation()

    assert first.content_sha256 == second.content_sha256
    assert len(first.content_sha256) == 64
    assert first.frames[0].sha256 != first.frames[1].sha256


def test_rgb_frame_rejects_wrong_payload_size() -> None:
    with pytest.raises(ValueError, match="RGB payload size"):
        RGBFrame("agentview", height=2, width=2, data=b"too short")


def test_robot_observation_rejects_non_finite_proprio() -> None:
    with pytest.raises(ValueError, match="finite"):
        RobotObservation(
            context_id="context-0",
            task="task",
            frames=(RGBFrame("agentview", height=1, width=1, data=b"\x00\x00\x00"),),
            proprio=(math.nan,),
            proprio_fields=("eef_x",),
        )


def test_action_prediction_validates_shape_and_runtime() -> None:
    runtime = InferenceRuntime(
        device="cuda:0",
        dtype="bfloat16",
        latency_seconds=1.25,
        peak_allocated_bytes=100,
        peak_reserved_bytes=120,
    )
    prediction = ActionPrediction(
        model_id="starwam-wan22-5b-mot-libero",
        context_id="context-0",
        action_space="libero-eef-delta-pose-gripper-v1",
        actions=((0.0, 0.1, 0.2), (0.3, 0.4, 0.5)),
        seed=42,
        runtime=runtime,
    )

    assert prediction.horizon == 2
    assert prediction.action_dim == 3
    assert prediction.to_dict()["runtime"] == runtime.to_dict()

    with pytest.raises(ValueError, match="same dimension"):
        ActionPrediction(
            model_id="model",
            context_id="context-0",
            action_space="space",
            actions=((0.0, 0.1), (0.2,)),
            seed=42,
            runtime=runtime,
        )
