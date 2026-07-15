from wamprobe.adapters.manipulation import (
    ActionAgnosticManipulationAdapter,
    CopyLastManipulationAdapter,
    NoisyManipulationAdapter,
    OracleManipulationAdapter,
    WrongDirectionManipulationAdapter,
)
from wamprobe.benchmarks.blockpush import BlockPush2D
from wamprobe.benchmarks.gripper_catch import GripperCatch
from wamprobe.manipulation_evaluation import evaluate_manipulation


def test_blockpush_has_precontact_and_contact_dynamics() -> None:
    benchmark = BlockPush2D(horizon=6)
    group = benchmark.make_suite(contexts=1, seed=7).groups[0]
    optimal = benchmark.optimal_action(group.context)

    trajectory = benchmark.rollout(group.context, optimal)
    noop = benchmark.rollout(group.context, group.actions[0])
    reversed_trajectory = benchmark.rollout(
        group.context,
        benchmark.reverse_action(optimal),
    )

    assert trajectory.states[0].object_position == group.context.initial_state.object_position
    assert any(state.in_contact for state in trajectory.states[1:])
    assert trajectory.final_state.object_position == group.context.goal
    assert noop.final_state.object_position == group.context.initial_state.object_position
    assert (
        reversed_trajectory.final_state.object_position
        == group.context.initial_state.object_position
    )


def test_manipulation_suite_generator_scales_to_public_pilot_size() -> None:
    for benchmark in (BlockPush2D(), GripperCatch()):
        suite = benchmark.make_suite(contexts=1000, seed=17)

        assert len(suite.groups) == 1000
        assert len({group.context.context_id for group in suite.groups}) == 1000
        assert suite == benchmark.make_suite(contexts=1000, seed=17)


def test_gripper_catch_requires_alignment_and_close_semantics() -> None:
    benchmark = GripperCatch(horizon=5)
    suite = benchmark.make_suite(contexts=3, seed=3)

    for group in suite.groups:
        optimal = benchmark.optimal_action(group.context)
        caught = benchmark.rollout(group.context, optimal)
        noop = benchmark.rollout(group.context, group.actions[0])

        assert caught.final_state.object_attached
        assert caught.final_state.gripper_closed
        assert caught.final_state.object_position == caught.final_state.effector_position
        assert not noop.final_state.object_attached
        assert benchmark.score(group.context, caught) > benchmark.score(group.context, noop)


def test_manipulation_rgb_observation_is_dependency_free_and_state_sensitive() -> None:
    for benchmark in (BlockPush2D(horizon=5), GripperCatch(horizon=5)):
        group = benchmark.make_suite(contexts=1, seed=2).groups[0]
        initial = benchmark.observe(group.context, group.context.initial_state)
        final_state = benchmark.rollout(
            group.context,
            benchmark.optimal_action(group.context),
        ).final_state
        final = benchmark.observe(group.context, final_state)

        assert initial.frames[0].height == 64
        assert initial.frames[0].width == 64
        assert len(initial.frames[0].data) == 64 * 64 * 3
        assert initial.content_sha256 != final.content_sha256


def test_noisy_manipulation_rollouts_are_content_addressed() -> None:
    benchmark = BlockPush2D(horizon=6)
    group = benchmark.make_suite(contexts=1, seed=4).groups[0]
    action = benchmark.optimal_action(group.context)

    first = benchmark.rollout(group.context, action, noise_std=0.01, seed=19)
    second = benchmark.rollout(group.context, action, noise_std=0.01, seed=19)
    changed_seed = benchmark.rollout(group.context, action, noise_std=0.01, seed=20)

    assert first == second
    assert first != changed_seed


def test_manipulation_baselines_produce_expected_metric_profiles() -> None:
    for benchmark in (BlockPush2D(horizon=6), GripperCatch(horizon=5)):
        suite = benchmark.make_suite(contexts=12, seed=11)
        oracle = evaluate_manipulation(
            OracleManipulationAdapter(benchmark), benchmark, suite, seed=29
        )
        noisy = evaluate_manipulation(
            NoisyManipulationAdapter(benchmark, noise_std=0.01),
            benchmark,
            suite,
            seed=29,
        )
        copy_last = evaluate_manipulation(CopyLastManipulationAdapter(), benchmark, suite, seed=29)
        wrong = evaluate_manipulation(
            WrongDirectionManipulationAdapter(benchmark), benchmark, suite, seed=29
        )
        action_agnostic = evaluate_manipulation(
            ActionAgnosticManipulationAdapter(benchmark), benchmark, suite, seed=29
        )

        assert oracle.metrics["state_fde"] == 0.0
        assert oracle.metrics["top1_regret"] == 0.0
        assert oracle.metrics["candidate_ranking_spearman"] == 1.0
        assert oracle.metrics["candidate_ranking_ndcg"] == 1.0
        assert 0.0 < noisy.metrics["state_fde"] < copy_last.metrics["state_fde"]
        assert wrong.metrics["state_fde"] > oracle.metrics["state_fde"]
        assert action_agnostic.metrics["candidate_ranking_spearman"] == 0.0
