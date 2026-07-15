"""Reference baselines used to sanity-check WAMProbe metrics."""

from __future__ import annotations

import hashlib
from random import Random

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


class NoisyLinearAdapter(_StateBaseline):
    """Action-aware linear dynamics with deterministic Gaussian transition noise."""

    model_id = "noisy-linear"

    def __init__(self, *, noise_std: float = 0.04) -> None:
        if noise_std <= 0:
            raise ValueError("noise_std must be positive")
        self._noise_std = noise_std

    def predict_future(
        self,
        context: Context2D,
        action: Action2D,
        *,
        horizon: int,
        seed: int,
    ) -> Trajectory2D:
        if horizon <= 0:
            raise ValueError("horizon must be positive")
        seed_material = f"{seed}\0{context.context_id}\0{action.name}".encode()
        local_seed = int.from_bytes(hashlib.sha256(seed_material).digest()[:8], "big")
        rng = Random(local_seed)
        position = context.position
        states: list[Vec2] = []
        for _ in range(horizon):
            noise = Vec2(rng.gauss(0.0, self._noise_std), rng.gauss(0.0, self._noise_std))
            position = position + action.delta + noise
            states.append(position)
        return Trajectory2D(context.context_id, action.name, tuple(states))


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
