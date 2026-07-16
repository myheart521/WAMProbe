"""A small reference bridge from an arbitrary backend to ``WAMAdapter``.

Replace ``LinearStateBackend`` with a wrapper around your model. Keep the
``StarterWAMAdapter`` validation boundary so benchmark inputs and model outputs
remain semantically aligned.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Protocol

from wamprobe.api.capabilities import FutureRepresentation, ModelCapabilities
from wamprobe.api.types import Action2D, Context2D, Trajectory2D, Vec2


@dataclass(frozen=True, slots=True)
class PredictionRequest:
    """Backend-neutral prediction request with explicit intervention semantics."""

    context_id: str
    action_name: str
    position_xy: tuple[float, float]
    goal_xy: tuple[float, float]
    action_delta_xy: tuple[float, float]
    horizon: int
    seed: int


class StateFutureBackend(Protocol):
    """Narrow interface that a custom state-future model must implement."""

    def predict_positions(
        self,
        request: PredictionRequest,
    ) -> tuple[tuple[float, float], ...]:
        """Return one predicted ``(x, y)`` state for every requested step."""

        ...


class LinearStateBackend:
    """Dependency-free example backend using the supplied action intervention."""

    def predict_positions(
        self,
        request: PredictionRequest,
    ) -> tuple[tuple[float, float], ...]:
        x, y = request.position_xy
        dx, dy = request.action_delta_xy
        return tuple((x + dx * step, y + dy * step) for step in range(1, request.horizon + 1))


class StarterWAMAdapter:
    """Validate and expose a custom state-future backend as a WAMProbe adapter."""

    def __init__(
        self,
        backend: StateFutureBackend,
        *,
        model_id: str = "starter-linear-state",
    ) -> None:
        self._backend = backend
        self._capabilities = ModelCapabilities(
            model_id=model_id,
            future_representation=FutureRepresentation.STATES,
            deterministic_seed=True,
        )

    @property
    def capabilities(self) -> ModelCapabilities:
        """Declare the output representation and deterministic seed behavior."""

        return self._capabilities

    def predict_future(
        self,
        context: Context2D,
        action: Action2D,
        *,
        horizon: int,
        seed: int,
    ) -> Trajectory2D:
        """Translate typed inputs, call the backend, and validate its state future."""

        if horizon <= 0:
            raise ValueError("horizon must be positive")
        request = PredictionRequest(
            context_id=context.context_id,
            action_name=action.name,
            position_xy=(context.position.x, context.position.y),
            goal_xy=(context.goal.x, context.goal.y),
            action_delta_xy=(action.delta.x, action.delta.y),
            horizon=horizon,
            seed=seed,
        )
        positions = self._backend.predict_positions(request)
        if len(positions) != horizon:
            raise ValueError(f"backend must return exactly {horizon} states")

        states: list[Vec2] = []
        for index, position in enumerate(positions):
            if len(position) != 2:
                raise ValueError(f"backend state {index} must contain exactly two coordinates")
            x, y = position
            if not math.isfinite(x) or not math.isfinite(y):
                raise ValueError(f"backend state {index} coordinates must be finite")
            states.append(Vec2(float(x), float(y)))
        return Trajectory2D(context.context_id, action.name, tuple(states))

    def close(self) -> None:
        """Release resources; the starter backend owns none."""
