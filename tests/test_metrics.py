from wamprobe.adapters.baselines import CopyLastFrameAdapter, OraclePointMassAdapter
from wamprobe.api.types import Context2D, Trajectory2D, Vec2
from wamprobe.benchmarks.pointmass import PointMass2D
from wamprobe.metrics import action_dependence_permutation_test, state_fde


def test_state_fde_measures_only_final_state_error() -> None:
    context = Context2D("context-0", Vec2(0.0, 0.0), Vec2(1.0, 0.0))
    predicted = Trajectory2D(
        context_id=context.context_id,
        action_name="right",
        states=(Vec2(100.0, 100.0), Vec2(0.75, 0.0)),
    )
    truth = Trajectory2D(
        context_id=context.context_id,
        action_name="right",
        states=(Vec2(0.5, 0.0), Vec2(1.0, 0.0)),
    )

    assert state_fde([(context, predicted, truth)]) == 0.25


def test_action_dependence_permutation_null_separates_oracle_from_copy_last() -> None:
    benchmark = PointMass2D(horizon=4)
    group = benchmark.make_suite(contexts=1, seed=7).groups[0]
    oracle = OraclePointMassAdapter(benchmark)
    copy_last = CopyLastFrameAdapter()

    oracle_samples = [
        (
            group.context,
            oracle.predict_future(group.context, action, horizon=4, seed=11),
            benchmark.rollout(group.context, action),
        )
        for action in group.actions
    ]
    copy_samples = [
        (
            group.context,
            copy_last.predict_future(group.context, action, horizon=4, seed=11),
            benchmark.rollout(group.context, action),
        )
        for action in group.actions
    ]

    oracle_result = action_dependence_permutation_test(oracle_samples, permutations=128, seed=19)
    copy_result = action_dependence_permutation_test(copy_samples, permutations=128, seed=19)

    assert oracle_result.observed == 1.0
    assert oracle_result.effect_size > 1.0
    assert oracle_result.p_value < 0.1
    assert oracle_result == action_dependence_permutation_test(
        oracle_samples, permutations=128, seed=19
    )
    assert copy_result.observed == 0.0
    assert copy_result.effect_size == 0.0
    assert copy_result.p_value == 1.0
