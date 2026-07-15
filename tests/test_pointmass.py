from wamprobe.api.types import Action2D, Context2D, Vec2
from wamprobe.benchmarks.pointmass import PointMass2D


def test_pointmass_rollout_applies_action_each_step() -> None:
    benchmark = PointMass2D(horizon=4)
    context = Context2D("context-0", position=Vec2(0.0, 0.0), goal=Vec2(1.0, 0.0))
    action = Action2D("right", Vec2(0.25, 0.0))

    trajectory = benchmark.rollout(context, action)

    assert trajectory.states == (
        Vec2(0.25, 0.0),
        Vec2(0.5, 0.0),
        Vec2(0.75, 0.0),
        Vec2(1.0, 0.0),
    )
    assert benchmark.score(context, trajectory) == 0.0


def test_counterfactual_suite_shares_context_and_has_noop() -> None:
    benchmark = PointMass2D(horizon=4)

    suite = benchmark.make_suite(contexts=6, seed=7)

    assert len(suite.groups) == 6
    assert all(group.actions[0].name == "noop" for group in suite.groups)
    assert all(len({action.name for action in group.actions}) == 5 for group in suite.groups)
