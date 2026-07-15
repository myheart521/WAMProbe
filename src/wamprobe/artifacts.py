"""Versioned, deterministic prediction-cache artifacts."""

from __future__ import annotations

import hashlib
import json
import math
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from wamprobe.api.errors import ValidationError
from wamprobe.api.robotics import ActionPrediction, RobotObservation


def _validate_hex_digest(value: str, length: int, field_name: str) -> None:
    if len(value) != length or any(character not in "0123456789abcdef" for character in value):
        raise ValueError(f"{field_name} must be a lowercase {length}-character hex digest")


def _stable_sha256(value: object) -> str:
    encoded = json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True, slots=True)
class ModelProvenance:
    """Immutable code and checkpoint identity for a prediction."""

    adapter_version: str
    upstream_code_revision: str
    model_revision: str
    backbone_revision: str
    checkpoint_sha256: str
    vae_sha256: str
    text_encoder_sha256: str

    def __post_init__(self) -> None:
        if not self.adapter_version.strip():
            raise ValueError("adapter_version must not be empty")
        _validate_hex_digest(self.upstream_code_revision, 40, "upstream_code_revision")
        _validate_hex_digest(self.model_revision, 40, "model_revision")
        _validate_hex_digest(self.backbone_revision, 40, "backbone_revision")
        _validate_hex_digest(self.checkpoint_sha256, 64, "checkpoint_sha256")
        _validate_hex_digest(self.vae_sha256, 64, "vae_sha256")
        _validate_hex_digest(self.text_encoder_sha256, 64, "text_encoder_sha256")

    def to_dict(self) -> dict[str, object]:
        """Return JSON-compatible model provenance."""

        return {
            "adapter_version": self.adapter_version,
            "upstream_code_revision": self.upstream_code_revision,
            "model_revision": self.model_revision,
            "backbone_revision": self.backbone_revision,
            "checkpoint_sha256": self.checkpoint_sha256,
            "vae_sha256": self.vae_sha256,
            "text_encoder_sha256": self.text_encoder_sha256,
        }


@dataclass(frozen=True, slots=True)
class ResolvedPreprocessing:
    """Every model-visible preprocessing and normalization choice."""

    camera_order: tuple[str, ...]
    camera_transforms: tuple[str, ...]
    source_size: tuple[int, int]
    resized_camera_size: tuple[int, int]
    model_size: tuple[int, int]
    resize_interpolation: str
    channel_order: str
    tensor_layout: str
    camera_concatenation: Literal["horizontal", "vertical"]
    input_value_range: tuple[float, float]
    text_prompt: str
    text_cache_sha256: str
    proprio_fields: tuple[str, ...]
    action_normalization: str
    action_stats_sha256: str

    def __post_init__(self) -> None:
        if not self.camera_order or any(not item.strip() for item in self.camera_order):
            raise ValueError("camera_order must contain non-empty names")
        if len(self.camera_order) != len(set(self.camera_order)):
            raise ValueError("camera_order names must be unique")
        if len(self.camera_transforms) != len(self.camera_order):
            raise ValueError("camera_transforms must align with camera_order")
        if any(item not in {"identity", "rotate_180"} for item in self.camera_transforms):
            raise ValueError("camera transforms must be identity or rotate_180")
        if any(
            value <= 0 for value in (*self.source_size, *self.resized_camera_size, *self.model_size)
        ):
            raise ValueError("source, resized camera, and model image sizes must be positive")
        if self.resize_interpolation != "PIL_BILINEAR":
            raise ValueError("resize_interpolation must be PIL_BILINEAR")
        if self.channel_order != "RGB":
            raise ValueError("channel_order must be RGB")
        if self.tensor_layout != "BCHW":
            raise ValueError("tensor_layout must be BCHW")
        if self.camera_concatenation not in {"horizontal", "vertical"}:
            raise ValueError("camera_concatenation must be horizontal or vertical")
        resized_height, resized_width = self.resized_camera_size
        camera_count = len(self.camera_order)
        expected_model_size = (
            (resized_height, resized_width * camera_count)
            if self.camera_concatenation == "horizontal"
            else (resized_height * camera_count, resized_width)
        )
        if self.model_size != expected_model_size:
            raise ValueError(
                "model_size does not match resized cameras and concatenation: "
                f"expected {expected_model_size}"
            )
        low, high = self.input_value_range
        if not math.isfinite(low) or not math.isfinite(high) or low >= high:
            raise ValueError("input_value_range must contain finite increasing values")
        if not self.text_prompt.strip():
            raise ValueError("text_prompt must not be empty")
        _validate_hex_digest(self.text_cache_sha256, 64, "text_cache_sha256")
        if any(not field.strip() for field in self.proprio_fields):
            raise ValueError("proprio_fields must not contain empty names")
        if not self.action_normalization.strip():
            raise ValueError("action_normalization must not be empty")
        _validate_hex_digest(self.action_stats_sha256, 64, "action_stats_sha256")

    def to_dict(self) -> dict[str, object]:
        """Return JSON-compatible preprocessing metadata."""

        return {
            "camera_order": list(self.camera_order),
            "camera_transforms": list(self.camera_transforms),
            "source_size": list(self.source_size),
            "resized_camera_size": list(self.resized_camera_size),
            "model_size": list(self.model_size),
            "resize_interpolation": self.resize_interpolation,
            "channel_order": self.channel_order,
            "tensor_layout": self.tensor_layout,
            "camera_concatenation": self.camera_concatenation,
            "input_value_range": list(self.input_value_range),
            "text_prompt": self.text_prompt,
            "text_cache_sha256": self.text_cache_sha256,
            "proprio_fields": list(self.proprio_fields),
            "action_normalization": self.action_normalization,
            "action_stats_sha256": self.action_stats_sha256,
        }


@dataclass(frozen=True, slots=True)
class ResolvedInference:
    """Every output-affecting StarWAM action-sampling choice."""

    engine: str
    num_inference_steps: int
    scheduler: str
    scheduler_shift: float
    video_conditioning: str
    vae_device: str
    sampled_video_frames: int

    def __post_init__(self) -> None:
        if not self.engine.strip() or not self.scheduler.strip():
            raise ValueError("inference engine and scheduler must not be empty")
        if self.num_inference_steps <= 0:
            raise ValueError("num_inference_steps must be positive")
        if not math.isfinite(self.scheduler_shift) or self.scheduler_shift <= 0:
            raise ValueError("scheduler_shift must be finite and positive")
        if self.video_conditioning not in {"first_frame", "full_video"}:
            raise ValueError("video_conditioning must be first_frame or full_video")
        if not self.vae_device.strip():
            raise ValueError("vae_device must not be empty")
        if self.sampled_video_frames <= 0:
            raise ValueError("sampled_video_frames must be positive")

    def to_dict(self) -> dict[str, object]:
        """Return JSON-compatible inference settings."""

        return {
            "engine": self.engine,
            "num_inference_steps": self.num_inference_steps,
            "scheduler": self.scheduler,
            "scheduler_shift": self.scheduler_shift,
            "video_conditioning": self.video_conditioning,
            "vae_device": self.vae_device,
            "sampled_video_frames": self.sampled_video_frames,
        }


@dataclass(frozen=True, slots=True)
class ActionPredictionArtifact:
    """One cacheable observation-to-action result with full provenance."""

    observation: RobotObservation
    prediction: ActionPrediction
    provenance: ModelProvenance
    preprocessing: ResolvedPreprocessing
    inference: ResolvedInference
    schema_version: str = "0.1"

    def __post_init__(self) -> None:
        if self.schema_version != "0.1":
            raise ValueError(f"unsupported action artifact schema: {self.schema_version}")
        if self.observation.context_id != self.prediction.context_id:
            raise ValidationError("observation and prediction context_id values do not match")
        frame_names = tuple(frame.camera_name for frame in self.observation.frames)
        if frame_names != self.preprocessing.camera_order:
            raise ValidationError("observation frame order does not match resolved preprocessing")
        if self.observation.proprio_fields != self.preprocessing.proprio_fields:
            raise ValidationError("observation proprio fields do not match resolved preprocessing")

    @property
    def cache_key(self) -> str:
        """Return a deterministic key over inputs, seed, model, and preprocessing."""

        key_payload = {
            "schema_version": self.schema_version,
            "observation": self.observation.descriptor(),
            "model_id": self.prediction.model_id,
            "seed": self.prediction.seed,
            "provenance": self.provenance.to_dict(),
            "preprocessing": self.preprocessing.to_dict(),
            "inference": self.inference.to_dict(),
        }
        encoded = json.dumps(
            key_payload,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def to_dict(self) -> dict[str, object]:
        """Return the complete JSON-compatible cache artifact."""

        prediction = self.prediction.to_dict()
        return {
            "schema_version": self.schema_version,
            "cache_key": self.cache_key,
            "provenance": self.provenance.to_dict(),
            "observation": self.observation.descriptor(),
            "preprocessing": self.preprocessing.to_dict(),
            "inference": self.inference.to_dict(),
            "prediction": prediction,
            "prediction_sha256": _stable_sha256(prediction),
        }

    def write_json(self, path: Path) -> None:
        """Atomically write the artifact without persisting raw RGB bytes."""

        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
        try:
            temporary.write_text(
                json.dumps(
                    self.to_dict(),
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
