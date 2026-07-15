from dataclasses import replace

import pytest

from wamprobe.adapters.starwam import (
    StarWAMAdapter,
    StarWAMBackendResult,
    StarWAMRelease,
)
from wamprobe.api.capabilities import FutureRepresentation
from wamprobe.api.errors import ValidationError
from wamprobe.api.robotics import InferenceRuntime, RGBFrame, RobotObservation


class FakeStarWAMBackend:
    def __init__(self) -> None:
        self.calls: list[tuple[str, int]] = []
        self.closed = False

    def infer_action(self, observation: RobotObservation, *, seed: int) -> StarWAMBackendResult:
        self.calls.append((observation.context_id, seed))
        return StarWAMBackendResult(
            actions=((0.1,) * 7, (0.2,) * 7),
            runtime=InferenceRuntime(
                device="cpu",
                dtype="float32",
                latency_seconds=0.01,
                peak_allocated_bytes=0,
                peak_reserved_bytes=0,
            ),
        )

    def close(self) -> None:
        self.closed = True


def _observation() -> RobotObservation:
    return RobotObservation(
        context_id="libero-context-0",
        task="pick up the bowl",
        frames=(RGBFrame("agentview", 1, 1, b"\x00\x01\x02"),),
        proprio=(0.0,) * 8,
        proprio_fields=StarWAMRelease.proprio_fields(),
    )


def test_starwam_adapter_declares_only_verified_capabilities() -> None:
    adapter = StarWAMAdapter(FakeStarWAMBackend(), release=StarWAMRelease(action_horizon=2))

    capabilities = adapter.capabilities

    assert capabilities.model_id == "starwam-wan22-5b-mot-libero"
    assert capabilities.future_representation is FutureRepresentation.NONE
    assert capabilities.predicts_actions is True
    assert capabilities.scores_actions is False
    assert capabilities.exposes_world_features is False
    assert capabilities.stochastic is True
    assert capabilities.deterministic_seed is True


def test_starwam_adapter_returns_typed_action_prediction_and_closes_backend() -> None:
    backend = FakeStarWAMBackend()
    adapter = StarWAMAdapter(backend, release=StarWAMRelease(action_horizon=2))

    prediction = adapter.predict_action(_observation(), seed=42)
    adapter.close()

    assert prediction.context_id == "libero-context-0"
    assert prediction.action_space == "libero-eef-delta-pose-gripper-v1"
    assert prediction.horizon == 2
    assert prediction.action_dim == 7
    assert backend.calls == [("libero-context-0", 42)]
    assert backend.closed is True


def test_starwam_adapter_rejects_backend_horizon_mismatch() -> None:
    backend = FakeStarWAMBackend()
    release = replace(StarWAMRelease(action_horizon=2), action_horizon=3)
    adapter = StarWAMAdapter(backend, release=release)

    with pytest.raises(ValidationError, match="action horizon"):
        adapter.predict_action(_observation(), seed=42)
