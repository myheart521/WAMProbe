"""Analytic planar block-pushing benchmark with explicit contact phases."""

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


class BlockPush2D:
    """Known two-stage dynamics: approach first, then contact-driven object motion."""

    benchmark_id = "blockpush-2d-v0.1"

    def __init__(self, *, horizon: int = 6, action_scale: float = 0.06) -> None:
        if horizon < 3:
            raise ValueError("BlockPush horizon must be at least three")
        if action_scale <= 0:
            raise ValueError("action_scale must be positive")
        self.horizon = horizon
        self.action_scale = action_scale
        self._contact_reach = action_scale * 2.2

    def actions(self) -> tuple[ManipulationAction, ...]:
        """Return no-op and four constant planar push candidates."""

        scale = self.action_scale
        return (
            ManipulationAction("noop", Vec2(0.0, 0.0)),
            ManipulationAction("push-right", Vec2(scale, 0.0)),
            ManipulationAction("push-left", Vec2(-scale, 0.0)),
            ManipulationAction("push-up", Vec2(0.0, scale)),
            ManipulationAction("push-down", Vec2(0.0, -scale)),
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
        """Advance the pusher and move the block only after directed contact."""

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
            commanded_delta = action.effector_delta + noise
            object_direction = state.object_position - state.effector_position
            directed_toward_object = commanded_delta.dot(object_direction) > 1e-15
            can_reach = object_direction.norm() <= self._contact_reach
            in_contact = directed_toward_object and can_reach
            object_position = (
                state.object_position + commanded_delta if in_contact else state.object_position
            )
            state = ManipulationState(
                effector_position=state.effector_position + commanded_delta,
                object_position=object_position,
                in_contact=in_contact,
            )
            states.append(state)
        return ManipulationTrajectory(context.context_id, action.name, tuple(states))

    def score(self, context: ManipulationContext, trajectory: ManipulationTrajectory) -> float:
        """Return negative final block distance to the object-space goal."""

        return -(trajectory.final_state.object_position - context.goal).norm()

    def make_suite(self, *, contexts: int = 8, seed: int = 0) -> ManipulationInterventionSuite:
        """Generate paired pushes with one analytically optimal contact direction."""

        if contexts <= 0:
            raise ValueError("contexts must be positive")
        rng = Random(seed)
        candidates = self.actions()
        directions = candidates[1:]
        groups: list[ManipulationInterventionGroup] = []
        for index in range(contexts):
            optimal = directions[index % len(directions)]
            block = Vec2(rng.uniform(-0.2, 0.2), rng.uniform(-0.2, 0.2))
            pusher = block - optimal.effector_delta * 3.0
            goal = block + optimal.effector_delta * (self.horizon - 1)
            context = ManipulationContext(
                context_id=f"blockpush-context-{index:04d}",
                initial_state=ManipulationState(pusher, block),
                goal=goal,
            )
            groups.append(ManipulationInterventionGroup(context, candidates))
        return ManipulationInterventionSuite(self.benchmark_id, tuple(groups))

    def optimal_action(self, context: ManipulationContext) -> ManipulationAction:
        """Select the candidate aligned with block-to-goal displacement."""

        desired = context.goal - context.initial_state.object_position
        return max(self.actions()[1:], key=lambda action: action.effector_delta.dot(desired))

    def reverse_action(self, action: ManipulationAction) -> ManipulationAction:
        """Reverse planar motion while retaining branch identity."""

        return ManipulationAction(action.name, action.effector_delta * -1.0)

    def observe(self, context: ManipulationContext, state: ManipulationState) -> RobotObservation:
        """Return a 64×64 RGB view and explicit planar state fields."""

        frame = render_scene(
            effector_position=state.effector_position,
            object_position=state.object_position,
            goal=context.goal,
            gripper_closed=False,
            object_attached=False,
        )
        return RobotObservation(
            context_id=context.context_id,
            task="push the block to the green target",
            frames=(frame,),
            proprio=(
                state.effector_position.x,
                state.effector_position.y,
                state.object_position.x,
                state.object_position.y,
                float(state.in_contact),
            ),
            proprio_fields=(
                "pusher_x",
                "pusher_y",
                "block_x",
                "block_y",
                "in_contact",
            ),
        )
