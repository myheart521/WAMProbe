"""Analytic falling-object catch benchmark with explicit gripper attachment."""

from __future__ import annotations

import hashlib
from random import Random

from wamprobe.api.manipulation import (
    ManipulationAction,
    ManipulationContext,
    ManipulationInterventionGroup,
    ManipulationInterventionSuite,
    ManipulationState,
    ManipulationTrajectory,
)
from wamprobe.api.robotics import RobotObservation
from wamprobe.api.types import Vec2
from wamprobe.benchmarks.rendering import render_scene


class GripperCatch:
    """Falling-object dynamics where attachment requires alignment and closure."""

    benchmark_id = "gripper-catch-v0.1"

    def __init__(self, *, horizon: int = 5, action_scale: float = 0.04) -> None:
        if horizon < 3:
            raise ValueError("GripperCatch horizon must be at least three")
        if action_scale <= 0:
            raise ValueError("action_scale must be positive")
        self.horizon = horizon
        self.action_scale = action_scale
        self._gravity_step = 0.06
        self._catch_radius = 0.075

    def actions(self) -> tuple[ManipulationAction, ...]:
        """Return open no-op plus closed stationary/left/right catch candidates."""

        scale = self.action_scale
        return (
            ManipulationAction("noop", Vec2(0.0, 0.0), close_gripper=False),
            ManipulationAction("catch-left", Vec2(-scale, 0.0), close_gripper=True),
            ManipulationAction("catch-stay", Vec2(0.0, 0.0), close_gripper=True),
            ManipulationAction("catch-right", Vec2(scale, 0.0), close_gripper=True),
        )

    @staticmethod
    def _rng(context: ManipulationContext, action: ManipulationAction, seed: int) -> Random:
        material = f"{seed}\0{context.context_id}\0{action.name}".encode()
        local_seed = int.from_bytes(hashlib.sha256(material).digest()[:8], "big")
        return Random(local_seed)

    def rollout(
        self,
        context: ManipulationContext,
        action: ManipulationAction,
        *,
        noise_std: float = 0.0,
        seed: int = 0,
    ) -> ManipulationTrajectory:
        """Apply gravity and attach only when the closed gripper reaches the object."""

        if noise_std < 0:
            raise ValueError("noise_std must be non-negative")
        rng = self._rng(context, action, seed)
        state = context.initial_state
        states: list[ManipulationState] = []
        for _ in range(self.horizon):
            noise = (
                Vec2(rng.gauss(0.0, noise_std), rng.gauss(0.0, noise_std))
                if noise_std
                else Vec2(0.0, 0.0)
            )
            effector = state.effector_position + action.effector_delta + noise
            attached = state.object_attached and action.close_gripper
            if attached:
                object_position = effector
            else:
                object_position = Vec2(
                    state.object_position.x,
                    max(0.0, state.object_position.y - self._gravity_step),
                )
                if (
                    action.close_gripper
                    and (object_position - effector).norm() <= self._catch_radius
                ):
                    attached = True
                    object_position = effector
            state = ManipulationState(
                effector_position=effector,
                object_position=object_position,
                gripper_closed=action.close_gripper,
                object_attached=attached,
                in_contact=attached,
            )
            states.append(state)
        return ManipulationTrajectory(context.context_id, action.name, tuple(states))

    def score(self, context: ManipulationContext, trajectory: ManipulationTrajectory) -> float:
        """Reward a valid attachment, then prefer object proximity to the catch goal."""

        final = trajectory.final_state
        return float(final.object_attached) - (final.object_position - context.goal).norm()

    def make_suite(self, *, contexts: int = 8, seed: int = 0) -> ManipulationInterventionSuite:
        """Generate left/stationary/right catches from shared falling-object states."""

        if contexts <= 0:
            raise ValueError("contexts must be positive")
        rng = Random(seed)
        candidates = self.actions()
        catches = candidates[1:]
        groups: list[ManipulationInterventionGroup] = []
        for index in range(contexts):
            optimal = catches[index % len(catches)]
            initial_effector = Vec2(rng.uniform(-0.05, 0.05), 0.0)
            target_x = initial_effector.x + optimal.effector_delta.x * self.horizon
            goal = Vec2(target_x, 0.0)
            falling_object = Vec2(target_x, self._gravity_step * self.horizon)
            context = ManipulationContext(
                context_id=f"gripper-catch-context-{index:04d}",
                initial_state=ManipulationState(initial_effector, falling_object),
                goal=goal,
            )
            groups.append(ManipulationInterventionGroup(context, candidates))
        return ManipulationInterventionSuite(self.benchmark_id, tuple(groups))

    def optimal_action(self, context: ManipulationContext) -> ManipulationAction:
        """Select the closed command whose endpoint aligns with the falling object."""

        initial_x = context.initial_state.effector_position.x
        return min(
            self.actions()[1:],
            key=lambda action: abs(
                initial_x + action.effector_delta.x * self.horizon - context.goal.x
            ),
        )

    def reverse_action(self, action: ManipulationAction) -> ManipulationAction:
        """Invert motion and open the gripper for deliberately wrong dynamics."""

        if action.name == "noop":
            return action
        return ManipulationAction(
            action.name,
            action.effector_delta * -1.0,
            close_gripper=False,
        )

    def observe(self, context: ManipulationContext, state: ManipulationState) -> RobotObservation:
        """Return a 64×64 RGB view and explicit catch-state fields."""

        frame = render_scene(
            effector_position=state.effector_position,
            object_position=state.object_position,
            goal=context.goal,
            gripper_closed=state.gripper_closed,
            object_attached=state.object_attached,
        )
        return RobotObservation(
            context_id=context.context_id,
            task="catch the falling object with the gripper",
            frames=(frame,),
            proprio=(
                state.effector_position.x,
                state.effector_position.y,
                state.object_position.x,
                state.object_position.y,
                float(state.gripper_closed),
                float(state.object_attached),
            ),
            proprio_fields=(
                "gripper_x",
                "gripper_y",
                "object_x",
                "object_y",
                "gripper_closed",
                "object_attached",
            ),
        )
