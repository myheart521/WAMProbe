import pytest

from wamprobe.api.types import Action2D, Context2D, InterventionGroup, Trajectory2D, Vec2


def test_vec2_arithmetic_and_norm() -> None:
    start = Vec2(1.0, -2.0)
    delta = Vec2(0.5, 2.0)

    assert start + delta == Vec2(1.5, 0.0)
    assert start - delta == Vec2(0.5, -4.0)
    assert delta * 2 == Vec2(1.0, 4.0)
    assert Vec2(3.0, 4.0).norm() == 5.0


def test_trajectory_requires_at_least_one_state() -> None:
    with pytest.raises(ValueError, match="at least one state"):
        Trajectory2D(context_id="context-0", action_name="noop", states=())


def test_intervention_group_rejects_duplicate_action_names() -> None:
    context = Context2D("context-0", position=Vec2(0.0, 0.0), goal=Vec2(1.0, 0.0))
    duplicate_actions = (
        Action2D("right", Vec2(0.25, 0.0)),
        Action2D("right", Vec2(0.5, 0.0)),
    )

    with pytest.raises(ValueError, match="unique"):
        InterventionGroup(context=context, actions=duplicate_actions)
