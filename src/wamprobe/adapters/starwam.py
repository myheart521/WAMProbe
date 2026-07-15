"""Dependency-isolated contract wrapper for the pinned StarWAM release."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from wamprobe.api.capabilities import FutureRepresentation, ModelCapabilities
from wamprobe.api.errors import ValidationError
from wamprobe.api.robotics import ActionPrediction, InferenceRuntime, RobotObservation


@dataclass(frozen=True, slots=True)
class StarWAMRelease:
    """Verified public contract for the first StarWAM checkpoint."""

    model_id: str = "starwam-wan22-5b-mot-libero"
    action_space: str = "libero-eef-delta-pose-gripper-v1"
    action_horizon: int = 32
    action_dim: int = 7
    upstream_code_revision: str = "f6c771fc3be0a9bc271ea4f1531d8ea35efb0ec7"
    model_revision: str = "7d4bfe3ec76172ca17169fa959d21da099d386fe"
    checkpoint_sha256: str = "d24edea01579880327cfd9dc84d24adab82e420dca9652e614ad697bc8cc5378"
    action_stats_sha256: str = "9f65fb518ca446e0d5ca9e8127e960fe3d11e6466e4f48ba9bb1135b1e0fb4f0"

    def __post_init__(self) -> None:
        if self.action_horizon <= 0 or self.action_dim <= 0:
            raise ValueError("StarWAM action horizon and dimension must be positive")

    @staticmethod
    def proprio_fields() -> tuple[str, ...]:
        """Return the exact eight-dimensional upstream proprio ordering."""

        return (
            "eef_x",
            "eef_y",
            "eef_z",
            "axis_angle_x",
            "axis_angle_y",
            "axis_angle_z",
            "gripper_qpos_0",
            "gripper_qpos_1",
        )


@dataclass(frozen=True, slots=True)
class StarWAMBackendResult:
    """Raw result returned by an isolated StarWAM runtime backend."""

    actions: tuple[tuple[float, ...], ...]
    runtime: InferenceRuntime


class StarWAMBackend(Protocol):
    """Small seam implemented inside the optional PyTorch environment."""

    def infer_action(
        self,
        observation: RobotObservation,
        *,
        seed: int,
    ) -> StarWAMBackendResult:
        """Run one denormalized action-chunk prediction."""

        ...

    def close(self) -> None:
        """Release model and accelerator resources."""

        ...


class StarWAMAdapter:
    """Validate StarWAM inputs/outputs while keeping heavy dependencies isolated."""

    def __init__(self, backend: StarWAMBackend, *, release: StarWAMRelease | None = None) -> None:
        self._backend = backend
        self._release = release or StarWAMRelease()

    @property
    def release(self) -> StarWAMRelease:
        """Return immutable upstream and action-space provenance."""

        return self._release

    @property
    def capabilities(self) -> ModelCapabilities:
        """Declare only behavior verified for the released MoT checkpoint."""

        return ModelCapabilities(
            model_id=self._release.model_id,
            future_representation=FutureRepresentation.NONE,
            predicts_actions=True,
            scores_actions=False,
            exposes_world_features=False,
            stochastic=True,
            deterministic_seed=True,
            supports_batching=False,
        )

    def predict_action(self, observation: RobotObservation, *, seed: int) -> ActionPrediction:
        """Predict and validate one denormalized LIBERO action chunk."""

        if observation.proprio_fields != self._release.proprio_fields():
            raise ValidationError("StarWAM observation proprio fields do not match the release")
        result = self._backend.infer_action(observation, seed=seed)
        if len(result.actions) != self._release.action_horizon:
            raise ValidationError(
                "StarWAM backend action horizon does not match the release: "
                f"expected {self._release.action_horizon}, got {len(result.actions)}"
            )
        if any(len(action) != self._release.action_dim for action in result.actions):
            raise ValidationError(
                "StarWAM backend action dimension does not match the release: "
                f"expected {self._release.action_dim}"
            )
        try:
            return ActionPrediction(
                model_id=self._release.model_id,
                context_id=observation.context_id,
                action_space=self._release.action_space,
                actions=result.actions,
                seed=seed,
                runtime=result.runtime,
            )
        except ValueError as error:
            raise ValidationError(f"invalid StarWAM backend prediction: {error}") from error

    def close(self) -> None:
        """Release resources owned by the isolated backend."""

        self._backend.close()
