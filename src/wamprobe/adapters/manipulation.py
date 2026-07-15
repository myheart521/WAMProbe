"""Reference baselines for dependency-free analytic manipulation benchmarks."""

from __future__ import annotations

from wamprobe.api.capabilities import FutureRepresentation, ModelCapabilities
from wamprobe.api.manipulation import (
    ManipulationAction,
    ManipulationBenchmark,
    ManipulationContext,
    ManipulationTrajectory,
)


class _ManipulationBaseline:
    model_id = "manipulation-baseline"

    @property
    def capabilities(self) -> ModelCapabilities:
        return ModelCapabilities(
            model_id=self.model_id,
            future_representation=FutureRepresentation.STATES,
        )

    def close(self) -> None:
        """Analytic baselines own no external resources."""


class OracleManipulationAdapter(_ManipulationBaseline):
    """Upper bound backed by the benchmark's exact transition function."""

    model_id = "oracle-simulator"

    def __init__(self, benchmark: ManipulationBenchmark) -> None:
        self._benchmark = benchmark

    def predict_future(
        self,
        context: ManipulationContext,
        action: ManipulationAction,
        *,
        horizon: int,
        seed: int,
    ) -> ManipulationTrajectory:
        if horizon != self._benchmark.horizon:
            raise ValueError("adapter and benchmark horizons must match")
        return self._benchmark.rollout(context, action, seed=seed)


class NoisyManipulationAdapter(_ManipulationBaseline):
    """Action-aware benchmark dynamics with seeded transition noise."""

    model_id = "noisy-dynamics"

    def __init__(self, benchmark: ManipulationBenchmark, *, noise_std: float = 0.01) -> None:
        if noise_std <= 0:
            raise ValueError("noise_std must be positive")
        self._benchmark = benchmark
        self._noise_std = noise_std

    def predict_future(
        self,
        context: ManipulationContext,
        action: ManipulationAction,
        *,
        horizon: int,
        seed: int,
    ) -> ManipulationTrajectory:
        if horizon != self._benchmark.horizon:
            raise ValueError("adapter and benchmark horizons must match")
        return self._benchmark.rollout(
            context,
            action,
            noise_std=self._noise_std,
            seed=seed,
        )


class CopyLastManipulationAdapter(_ManipulationBaseline):
    """Action-ignoring baseline that freezes the complete current state."""

    model_id = "copy-last-frame"

    def predict_future(
        self,
        context: ManipulationContext,
        action: ManipulationAction,
        *,
        horizon: int,
        seed: int,
    ) -> ManipulationTrajectory:
        del seed
        return ManipulationTrajectory(
            context.context_id,
            action.name,
            (context.initial_state,) * horizon,
        )


class WrongDirectionManipulationAdapter(_ManipulationBaseline):
    """Deliberately reverse motion and, for catches, gripper semantics."""

    model_id = "wrong-direction"

    def __init__(self, benchmark: ManipulationBenchmark) -> None:
        self._benchmark = benchmark

    def predict_future(
        self,
        context: ManipulationContext,
        action: ManipulationAction,
        *,
        horizon: int,
        seed: int,
    ) -> ManipulationTrajectory:
        if horizon != self._benchmark.horizon:
            raise ValueError("adapter and benchmark horizons must match")
        reversed_trajectory = self._benchmark.rollout(
            context,
            self._benchmark.reverse_action(action),
            seed=seed,
        )
        return ManipulationTrajectory(
            context.context_id,
            action.name,
            reversed_trajectory.states,
        )


class ActionAgnosticManipulationAdapter(_ManipulationBaseline):
    """Predict the context-optimal future regardless of the candidate action."""

    model_id = "action-agnostic"

    def __init__(self, benchmark: ManipulationBenchmark) -> None:
        self._benchmark = benchmark

    def predict_future(
        self,
        context: ManipulationContext,
        action: ManipulationAction,
        *,
        horizon: int,
        seed: int,
    ) -> ManipulationTrajectory:
        if horizon != self._benchmark.horizon:
            raise ValueError("adapter and benchmark horizons must match")
        optimal = self._benchmark.rollout(
            context,
            self._benchmark.optimal_action(context),
            seed=seed,
        )
        return ManipulationTrajectory(context.context_id, action.name, optimal.states)
