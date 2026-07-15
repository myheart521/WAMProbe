"""Dependency-free robot observations and action predictions."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass


def _require_non_empty(value: str, field_name: str) -> None:
    if not value.strip():
        raise ValueError(f"{field_name} must not be empty")


@dataclass(frozen=True, slots=True)
class RGBFrame:
    """One tightly packed uint8 RGB observation frame."""

    camera_name: str
    height: int
    width: int
    data: bytes

    def __post_init__(self) -> None:
        _require_non_empty(self.camera_name, "camera_name")
        if self.height <= 0 or self.width <= 0:
            raise ValueError("RGB frame dimensions must be positive")
        expected_bytes = self.height * self.width * 3
        if len(self.data) != expected_bytes:
            raise ValueError(
                f"RGB payload size must be {expected_bytes} bytes, got {len(self.data)}"
            )

    @property
    def sha256(self) -> str:
        """Return a content checksum for cache identity and provenance."""

        return hashlib.sha256(self.data).hexdigest()

    def descriptor(self) -> dict[str, object]:
        """Return JSON metadata without embedding raw image bytes."""

        return {
            "camera_name": self.camera_name,
            "shape": [self.height, self.width, 3],
            "dtype": "uint8",
            "sha256": self.sha256,
        }


@dataclass(frozen=True, slots=True)
class RobotObservation:
    """A named robot context with explicit RGB and proprio semantics."""

    context_id: str
    task: str
    frames: tuple[RGBFrame, ...]
    proprio: tuple[float, ...]
    proprio_fields: tuple[str, ...]

    def __post_init__(self) -> None:
        _require_non_empty(self.context_id, "context_id")
        _require_non_empty(self.task, "task")
        if not self.frames:
            raise ValueError("robot observation requires at least one RGB frame")
        camera_names = [frame.camera_name for frame in self.frames]
        if len(camera_names) != len(set(camera_names)):
            raise ValueError("camera names must be unique")
        if len(self.proprio) != len(self.proprio_fields):
            raise ValueError("proprio values and fields must have the same length")
        if len(self.proprio_fields) != len(set(self.proprio_fields)):
            raise ValueError("proprio fields must be unique")
        if any(not field.strip() for field in self.proprio_fields):
            raise ValueError("proprio fields must not be empty")
        if any(not math.isfinite(value) for value in self.proprio):
            raise ValueError("proprio values must be finite")

    @property
    def content_sha256(self) -> str:
        """Return a stable digest over every model-visible observation input."""

        payload = {
            "context_id": self.context_id,
            "task": self.task,
            "frames": [frame.descriptor() for frame in self.frames],
            "proprio": list(self.proprio),
            "proprio_fields": list(self.proprio_fields),
        }
        encoded = json.dumps(
            payload,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def descriptor(self) -> dict[str, object]:
        """Return JSON metadata suitable for a cached prediction artifact."""

        return {
            "context_id": self.context_id,
            "task": self.task,
            "content_sha256": self.content_sha256,
            "frames": [frame.descriptor() for frame in self.frames],
            "proprio": list(self.proprio),
            "proprio_fields": list(self.proprio_fields),
        }


@dataclass(frozen=True, slots=True)
class InferenceRuntime:
    """Measured runtime and device data for one model call."""

    device: str
    dtype: str
    latency_seconds: float
    peak_allocated_bytes: int
    peak_reserved_bytes: int

    def __post_init__(self) -> None:
        _require_non_empty(self.device, "runtime device")
        _require_non_empty(self.dtype, "runtime dtype")
        if not math.isfinite(self.latency_seconds) or self.latency_seconds < 0:
            raise ValueError("latency_seconds must be finite and non-negative")
        if self.peak_allocated_bytes < 0 or self.peak_reserved_bytes < 0:
            raise ValueError("peak memory measurements must be non-negative")

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-compatible runtime record."""

        return {
            "device": self.device,
            "dtype": self.dtype,
            "latency_seconds": self.latency_seconds,
            "peak_allocated_bytes": self.peak_allocated_bytes,
            "peak_reserved_bytes": self.peak_reserved_bytes,
        }


@dataclass(frozen=True, slots=True)
class ActionPrediction:
    """A semantically named, denormalized robot action chunk."""

    model_id: str
    context_id: str
    action_space: str
    actions: tuple[tuple[float, ...], ...]
    seed: int
    runtime: InferenceRuntime

    def __post_init__(self) -> None:
        _require_non_empty(self.model_id, "model_id")
        _require_non_empty(self.context_id, "context_id")
        _require_non_empty(self.action_space, "action_space")
        if isinstance(self.seed, bool) or not isinstance(self.seed, int) or self.seed < 0:
            raise ValueError("seed must be a non-negative integer")
        if not self.actions or not self.actions[0]:
            raise ValueError("action prediction must contain a non-empty action chunk")
        action_dim = len(self.actions[0])
        if any(len(action) != action_dim for action in self.actions):
            raise ValueError("all predicted actions must have the same dimension")
        if any(not math.isfinite(value) for action in self.actions for value in action):
            raise ValueError("predicted actions must be finite")

    @property
    def horizon(self) -> int:
        """Return the number of predicted action steps."""

        return len(self.actions)

    @property
    def action_dim(self) -> int:
        """Return the action-vector width."""

        return len(self.actions[0])

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-compatible prediction record."""

        return {
            "model_id": self.model_id,
            "context_id": self.context_id,
            "action_space": self.action_space,
            "actions": [list(action) for action in self.actions],
            "horizon": self.horizon,
            "action_dim": self.action_dim,
            "seed": self.seed,
            "runtime": self.runtime.to_dict(),
        }
