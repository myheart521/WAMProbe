"""Analytic counterfactual benchmark for a two-dimensional point mass."""

from __future__ import annotations

from random import Random

from wamprobe.api.types import (
    Action2D,
    Context2D,
    InterventionGroup,
    InterventionSuite,
    Trajectory2D,
    Vec2,
)


class PointMass2D:
    """Known linear dynamics used to validate metrics before real WAMs."""

    benchmark_id = "pointmass-2d-v0.1"

    def __init__(self, *, horizon: int = 4, action_scale: float = 0.25) -> None:
        if horizon <= 0:
            raise ValueError("horizon must be positive")
        if action_scale <= 0:
            raise ValueError("action_scale must be positive")
        self.horizon = horizon
        self.action_scale = action_scale

    def actions(self) -> tuple[Action2D, ...]:
        """Return a deterministic, constraint-valid candidate action set."""

        scale = self.action_scale
        return (
            Action2D("noop", Vec2(0.0, 0.0)),
            Action2D("right", Vec2(scale, 0.0)),
            Action2D("left", Vec2(-scale, 0.0)),
            Action2D("up", Vec2(0.0, scale)),
            Action2D("down", Vec2(0.0, -scale)),
        )

    def rollout(self, context: Context2D, action: Action2D) -> Trajectory2D:
        """Apply the action once per step using exact linear dynamics."""

        position = context.position
        states: list[Vec2] = []
        for _ in range(self.horizon):
            position = position + action.delta
            states.append(position)
        return Trajectory2D(context.context_id, action.name, tuple(states))

    def score(self, context: Context2D, trajectory: Trajectory2D) -> float:
        """Return negative final distance to the context goal."""

        return -(trajectory.final_state - context.goal).norm()

    def make_suite(self, *, contexts: int = 8, seed: int = 0) -> InterventionSuite:
        """Build paired interventions whose optimal action is known exactly."""

        if contexts <= 0:
            raise ValueError("contexts must be positive")

        rng = Random(seed)
        candidates = self.actions()
        directional_actions = candidates[1:]
        groups: list[InterventionGroup] = []
        for index in range(contexts):
            start = Vec2(rng.uniform(-0.5, 0.5), rng.uniform(-0.5, 0.5))
            optimal = directional_actions[index % len(directional_actions)]
            goal = start + optimal.delta * self.horizon
            context = Context2D(f"context-{index:04d}", start, goal)
            groups.append(InterventionGroup(context, candidates))

        return InterventionSuite(self.benchmark_id, tuple(groups))
