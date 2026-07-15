"""Reference baselines used to sanity-check WAMProbe metrics."""

from __future__ import annotations

from wamprobe.api.capabilities import FutureRepresentation, ModelCapabilities
from wamprobe.api.types import Action2D, Context2D, Trajectory2D, Vec2
from wamprobe.benchmarks.pointmass import PointMass2D


class _StateBaseline:
    model_id = "state-baseline"

    @property
    def capabilities(self) -> ModelCapabilities:
        return ModelCapabilities(
            model_id=self.model_id,
            future_representation=FutureRepresentation.STATES,
        )

    def close(self) -> None:
        """Baselines own no external resources."""


class OraclePointMassAdapter(_StateBaseline):
    """Upper bound that uses the exact benchmark transition."""

    model_id = "oracle-pointmass"

    def __init__(self, benchmark: PointMass2D) -> None:
        self._benchmark = benchmark

    def predict_future(
        self,
        context: Context2D,
        action: Action2D,
        *,
        horizon: int,
        seed: int,
    ) -> Trajectory2D:
        del seed
        if horizon != self._benchmark.horizon:
            raise ValueError("adapter and benchmark horizons must match")
        return self._benchmark.rollout(context, action)


class CopyLastFrameAdapter(_StateBaseline):
    """Action-ignoring baseline that repeats the current state."""

    model_id = "copy-last-frame"

    def predict_future(
        self,
        context: Context2D,
        action: Action2D,
        *,
        horizon: int,
        seed: int,
    ) -> Trajectory2D:
        del seed
        return Trajectory2D(context.context_id, action.name, (context.position,) * horizon)


class WrongDirectionAdapter(_StateBaseline):
    """Action-dependent baseline that deliberately predicts the opposite direction."""

    model_id = "wrong-direction"

    def __init__(self, benchmark: PointMass2D) -> None:
        self._benchmark = benchmark

    def predict_future(
        self,
        context: Context2D,
        action: Action2D,
        *,
        horizon: int,
        seed: int,
    ) -> Trajectory2D:
        del seed
        if horizon != self._benchmark.horizon:
            raise ValueError("adapter and benchmark horizons must match")
        reversed_action = Action2D(action.name, action.delta * -1.0)
        return self._benchmark.rollout(context, reversed_action)


class ActionAgnosticAdapter(_StateBaseline):
    """Plausible-looking baseline that moves to the goal for every input action."""

    model_id = "action-agnostic"

    def predict_future(
        self,
        context: Context2D,
        action: Action2D,
        *,
        horizon: int,
        seed: int,
    ) -> Trajectory2D:
        del seed
        step = (context.goal - context.position) * (1.0 / horizon)
        position = context.position
        states: list[Vec2] = []
        for _ in range(horizon):
            position = position + step
            states.append(position)
        return Trajectory2D(context.context_id, action.name, tuple(states))
