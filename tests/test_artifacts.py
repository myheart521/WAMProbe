import json
from pathlib import Path

import pytest

from wamprobe.api.errors import ValidationError
from wamprobe.api.robotics import ActionPrediction, InferenceRuntime, RGBFrame, RobotObservation
from wamprobe.artifacts import (
    ActionPredictionArtifact,
    ModelProvenance,
    ResolvedInference,
    ResolvedPreprocessing,
)


def _inputs(seed: int = 42) -> tuple[RobotObservation, ActionPrediction]:
    observation = RobotObservation(
        context_id="libero-spatial-task0-init0-wait30",
        task="pick up the black bowl and place it on the plate",
        frames=(
            RGBFrame("agentview", 1, 1, b"\x01\x02\x03"),
            RGBFrame("wrist", 1, 1, b"\x04\x05\x06"),
        ),
        proprio=(0.0, 0.1),
        proprio_fields=("eef_x", "eef_y"),
    )
    prediction = ActionPrediction(
        model_id="starwam-wan22-5b-mot-libero",
        context_id=observation.context_id,
        action_space="libero-eef-delta-pose-gripper-v1",
        actions=((0.0,) * 7, (0.1,) * 7),
        seed=seed,
        runtime=InferenceRuntime("cuda:0", "bfloat16", 1.0, 100, 120),
    )
    return observation, prediction


def _artifact(seed: int = 42) -> ActionPredictionArtifact:
    observation, prediction = _inputs(seed)
    return ActionPredictionArtifact(
        observation=observation,
        prediction=prediction,
        provenance=ModelProvenance(
            adapter_version="0.1",
            upstream_code_revision="f" * 40,
            model_revision="7" * 40,
            backbone_revision="9" * 40,
            checkpoint_sha256="d" * 64,
            vae_sha256="2" * 64,
            text_encoder_sha256="c" * 64,
        ),
        preprocessing=ResolvedPreprocessing(
            camera_order=("agentview", "wrist"),
            camera_transforms=("rotate_180", "rotate_180"),
            source_size=(256, 256),
            resized_camera_size=(224, 224),
            model_size=(224, 448),
            resize_interpolation="PIL_BILINEAR",
            channel_order="RGB",
            tensor_layout="BCHW",
            camera_concatenation="horizontal",
            input_value_range=(-1.0, 1.0),
            text_prompt=(
                "A video recorded from a robot's point of view executing the following "
                "instruction: pick up the black bowl and place it on the plate"
            ),
            text_cache_sha256="a" * 64,
            proprio_fields=("eef_x", "eef_y"),
            action_normalization="minmax",
            action_stats_sha256="9" * 64,
        ),
        inference=ResolvedInference(
            engine="starwam_mot_infer_action",
            num_inference_steps=1,
            scheduler="continuous_flow_match_euler",
            scheduler_shift=5.0,
            video_conditioning="first_frame",
            vae_device="cpu",
            sampled_video_frames=9,
        ),
    )


def test_action_artifact_cache_key_is_stable_and_seed_sensitive() -> None:
    assert _artifact().cache_key == _artifact().cache_key
    assert _artifact(seed=42).cache_key != _artifact(seed=43).cache_key


def test_action_artifact_writes_atomic_json_without_raw_rgb(tmp_path: Path) -> None:
    artifact = _artifact()
    output = tmp_path / "prediction.json"

    artifact.write_json(output)

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "0.1"
    assert payload["cache_key"] == artifact.cache_key
    assert payload["observation"]["frames"][0]["sha256"]
    assert "data" not in payload["observation"]["frames"][0]
    assert payload["preprocessing"]["camera_transforms"] == ["rotate_180"] * 2
    assert payload["provenance"]["vae_sha256"] == "2" * 64
    assert payload["inference"]["num_inference_steps"] == 1
    assert payload["prediction"]["actions"][1] == [0.1] * 7


def test_action_artifact_rejects_mismatched_context() -> None:
    observation, prediction = _inputs()
    prediction = ActionPrediction(
        model_id=prediction.model_id,
        context_id="different-context",
        action_space=prediction.action_space,
        actions=prediction.actions,
        seed=prediction.seed,
        runtime=prediction.runtime,
    )

    with pytest.raises(ValidationError, match="context_id"):
        ActionPredictionArtifact(
            observation=observation,
            prediction=prediction,
            provenance=_artifact().provenance,
            preprocessing=_artifact().preprocessing,
            inference=_artifact().inference,
        )
