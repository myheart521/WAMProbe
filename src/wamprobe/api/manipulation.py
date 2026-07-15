"""Typed dependency-free contracts for analytic manipulation benchmarks."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from wamprobe.api.capabilities import ModelCapabilities
from wamprobe.api.robotics import RobotObservation
from wamprobe.api.types import Vec2


@dataclass(frozen=True, slots=True)
class ManipulationState:
    """Minimal planar robot/object state with explicit contact and grasp semantics."""

    effector_position: Vec2
    object_position: Vec2
    gripper_closed: bool = False
    object_attached: bool = False
    in_contact: bool = False

    def __post_init__(self) -> None:
        values = (
            self.effector_position.x,
            self.effector_position.y,
            self.object_position.x,
            self.object_position.y,
        )
        if any(not math.isfinite(value) for value in values):
            raise ValueError("manipulation state coordinates must be finite")
        if self.object_attached and not self.gripper_closed:
            raise ValueError("an attached object requires a closed gripper")

    def vector(self) -> tuple[float, ...]:
        """Return a metric-ready state vector with explicit semantic flags."""

        return (
            self.effector_position.x,
            self.effector_position.y,
            self.object_position.x,
            self.object_position.y,
            float(self.gripper_closed),
            float(self.object_attached),
            float(self.in_contact),
        )


@dataclass(frozen=True, slots=True)
class ManipulationContext:
    """Shared initial state and object-space goal for one intervention group."""

    context_id: str
    initial_state: ManipulationState
    goal: Vec2

    def __post_init__(self) -> None:
        if not self.context_id.strip():
            raise ValueError("context_id must not be empty")
        if not math.isfinite(self.goal.x) or not math.isfinite(self.goal.y):
            raise ValueError("manipulation goal coordinates must be finite")


@dataclass(frozen=True, slots=True)
class ManipulationAction:
    """Constant planar effector command plus explicit gripper-close semantics."""

    name: str
    effector_delta: Vec2
    close_gripper: bool = False

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("manipulation action name must not be empty")


@dataclass(frozen=True, slots=True)
class ManipulationTrajectory:
    """State rollout for one context/action branch."""

    context_id: str
    action_name: str
    states: tuple[ManipulationState, ...]

    def __post_init__(self) -> None:
        if not self.states:
            raise ValueError("manipulation trajectory must contain at least one state")

    @property
    def final_state(self) -> ManipulationState:
        """Return the final manipulation state."""

        return self.states[-1]


@dataclass(frozen=True, slots=True)
class ManipulationInterventionGroup:
    """Candidate actions branched from one manipulation context."""

    context: ManipulationContext
    actions: tuple[ManipulationAction, ...]

    def __post_init__(self) -> None:
        if len(self.actions) < 2:
            raise ValueError("a manipulation group requires at least two actions")
        names = [action.name for action in self.actions]
        if len(names) != len(set(names)):
            raise ValueError("manipulation action names must be unique")


@dataclass(frozen=True, slots=True)
class ManipulationInterventionSuite:
    """Versioned collection of analytic manipulation intervention groups."""

    benchmark_id: str
    groups: tuple[ManipulationInterventionGroup, ...]

    def __post_init__(self) -> None:
        if not self.benchmark_id.strip():
            raise ValueError("benchmark_id must not be empty")
        if not self.groups:
            raise ValueError("a manipulation suite requires at least one group")


@runtime_checkable
class ManipulationBenchmark(Protocol):
    """Known-dynamics benchmark used by manipulation adapters and evaluators."""

    benchmark_id: str
    horizon: int

    def actions(self) -> tuple[ManipulationAction, ...]:
        """Return the benchmark's candidate action set."""

        ...

    def rollout(
        self,
        context: ManipulationContext,
        action: ManipulationAction,
        *,
        noise_std: float = 0.0,
        seed: int = 0,
    ) -> ManipulationTrajectory:
        """Roll out known dynamics, optionally with seeded transition noise."""

        ...

    def score(self, context: ManipulationContext, trajectory: ManipulationTrajectory) -> float:
        """Score one candidate future using ground-truth task semantics."""

        ...

    def make_suite(self, *, contexts: int = 8, seed: int = 0) -> ManipulationInterventionSuite:
        """Generate deterministic paired interventions."""

        ...

    def optimal_action(self, context: ManipulationContext) -> ManipulationAction:
        """Return the analytically optimal candidate for a generated context."""

        ...

    def reverse_action(self, action: ManipulationAction) -> ManipulationAction:
        """Return a deliberately wrong semantic/directional command."""

        ...

    def observe(self, context: ManipulationContext, state: ManipulationState) -> RobotObservation:
        """Render a state as RGB plus named proprioception."""

        ...


@runtime_checkable
class ManipulationAdapter(Protocol):
    """Adapter protocol for analytic planar manipulation futures."""

    @property
    def capabilities(self) -> ModelCapabilities:
        """Describe the adapter output and runtime behavior."""

        ...

    def predict_future(
        self,
        context: ManipulationContext,
        action: ManipulationAction,
        *,
        horizon: int,
        seed: int,
    ) -> ManipulationTrajectory:
        """Predict a manipulation state trajectory."""

        ...

    def close(self) -> None:
        """Release adapter resources."""

        ...
