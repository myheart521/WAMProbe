from wamprobe.adapters.baselines import (
    ActionAgnosticAdapter,
    CopyLastFrameAdapter,
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
    assert copy_last.metrics["action_dependence"] == 0.0
    assert action_agnostic.metrics["action_dependence"] == 0.0
    assert oracle.metrics["top1_regret"] == 0.0
    assert action_agnostic.metrics["top1_regret"] > oracle.metrics["top1_regret"]


def test_noop_stability_catches_action_agnostic_motion() -> None:
    benchmark = PointMass2D(horizon=4)
    suite = benchmark.make_suite(contexts=4, seed=3)

    oracle = evaluate(OraclePointMassAdapter(benchmark), benchmark, suite)
    action_agnostic = evaluate(ActionAgnosticAdapter(), benchmark, suite)

    assert oracle.metrics["noop_stability"] == 1.0
    assert action_agnostic.metrics["noop_stability"] == 0.0
