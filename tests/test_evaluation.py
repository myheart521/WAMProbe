from wamprobe.adapters.baselines import (
    ActionAgnosticAdapter,
    CopyLastFrameAdapter,
    NoisyLinearAdapter,
    OraclePointMassAdapter,
    WrongDirectionAdapter,
)
from wamprobe.benchmarks.pointmass import PointMass2D
from wamprobe.evaluation import evaluate


def test_reference_baselines_have_expected_metric_ordering() -> None:
    benchmark = PointMass2D(horizon=4)
    suite = benchmark.make_suite(contexts=12, seed=11)

    oracle = evaluate(OraclePointMassAdapter(benchmark), benchmark, suite)
    copy_last = evaluate(CopyLastFrameAdapter(), benchmark, suite)
    wrong = evaluate(WrongDirectionAdapter(benchmark), benchmark, suite)
    action_agnostic = evaluate(ActionAgnosticAdapter(), benchmark, suite)

    assert oracle.metrics["counterfactual_direction_accuracy"] == 1.0
    assert wrong.metrics["counterfactual_direction_accuracy"] == -1.0
    assert oracle.metrics["state_ade"] == 0.0
    assert oracle.metrics["state_fde"] == 0.0
    assert copy_last.metrics["action_dependence"] == 0.0
    assert action_agnostic.metrics["action_dependence"] == 0.0
    assert oracle.metrics["top1_regret"] == 0.0
    assert action_agnostic.metrics["top1_regret"] > oracle.metrics["top1_regret"]
    assert oracle.metrics["action_dependence_permutation_effect"] > 1.0
    assert copy_last.metrics["action_dependence_permutation_effect"] == 0.0
    assert oracle.metrics["candidate_ranking_spearman"] == 1.0
    assert oracle.metrics["candidate_ranking_kendall_tau"] == 1.0
    assert oracle.metrics["candidate_ranking_ndcg"] == 1.0
    assert oracle.metrics["candidate_ranking_pairwise_accuracy"] == 1.0
    assert action_agnostic.metrics["candidate_ranking_spearman"] == 0.0
    assert all(result.metrics for result in oracle.context_results)


def test_noop_stability_catches_action_agnostic_motion() -> None:
    benchmark = PointMass2D(horizon=4)
    suite = benchmark.make_suite(contexts=4, seed=3)

    oracle = evaluate(OraclePointMassAdapter(benchmark), benchmark, suite)
    action_agnostic = evaluate(ActionAgnosticAdapter(), benchmark, suite)

    assert oracle.metrics["noop_stability"] == 1.0
    assert action_agnostic.metrics["noop_stability"] == 0.0


def test_noisy_linear_is_seeded_and_degrades_oracle_accuracy() -> None:
    benchmark = PointMass2D(horizon=4)
    suite = benchmark.make_suite(contexts=12, seed=11)

    first = evaluate(NoisyLinearAdapter(noise_std=0.04), benchmark, suite, seed=29)
    second = evaluate(NoisyLinearAdapter(noise_std=0.04), benchmark, suite, seed=29)

    assert first == second
    assert 0.0 < first.metrics["state_ade"] < 0.5
    assert 0.0 < first.metrics["state_fde"] < 1.0
    assert 0.9 < first.metrics["counterfactual_direction_accuracy"] < 1.0


def test_noisy_linear_metrics_degrade_monotonically_with_noise() -> None:
    benchmark = PointMass2D(horizon=4)
    suite = benchmark.make_suite(contexts=24, seed=11)

    results = [
        evaluate(NoisyLinearAdapter(noise_std=noise), benchmark, suite, seed=29)
        for noise in (0.01, 0.04, 0.12)
    ]

    assert [result.metrics["state_ade"] for result in results] == sorted(
        result.metrics["state_ade"] for result in results
    )
    assert [result.metrics["state_fde"] for result in results] == sorted(
        result.metrics["state_fde"] for result in results
    )
    assert [result.metrics["counterfactual_direction_accuracy"] for result in results] == sorted(
        (result.metrics["counterfactual_direction_accuracy"] for result in results),
        reverse=True,
    )
