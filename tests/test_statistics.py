import pytest

from wamprobe.adapters.baselines import CopyLastFrameAdapter, OraclePointMassAdapter
from wamprobe.benchmarks.pointmass import PointMass2D
from wamprobe.evaluation import evaluate
from wamprobe.stats import paired_metric_comparison, summarize


def test_context_bootstrap_summary_is_deterministic_and_reports_quantiles() -> None:
    first = summarize((1.0, 2.0, 3.0, 4.0), resamples=400, seed=17)
    second = summarize((1.0, 2.0, 3.0, 4.0), resamples=400, seed=17)

    assert first == second
    assert first.mean == 2.5
    assert first.median == 2.5
    assert first.standard_deviation == pytest.approx(1.11803398875)
    assert first.quantiles["p05"] == pytest.approx(1.15)
    assert first.quantiles["p95"] == pytest.approx(3.85)
    assert first.confidence_interval.lower <= first.mean <= first.confidence_interval.upper
    assert first.confidence_interval.unit == "context"


def test_constant_context_values_have_a_zero_width_bootstrap_interval() -> None:
    summary = summarize((3.0, 3.0, 3.0), resamples=100, seed=1)

    assert summary.confidence_interval.lower == 3.0
    assert summary.confidence_interval.upper == 3.0


def test_paired_metric_comparison_resamples_context_differences() -> None:
    benchmark = PointMass2D(horizon=4)
    suite = benchmark.make_suite(contexts=8, seed=5)
    oracle = evaluate(OraclePointMassAdapter(benchmark), benchmark, suite, seed=3)
    copy_last = evaluate(CopyLastFrameAdapter(), benchmark, suite, seed=3)

    comparison = paired_metric_comparison(
        oracle,
        copy_last,
        metric="state_fde",
        resamples=300,
        seed=23,
    )

    assert comparison.left_model == "oracle-pointmass"
    assert comparison.right_model == "copy-last-frame"
    assert comparison.contexts == 8
    # Four directional branches have FDE 1.0; the valid no-op branch has FDE 0.0.
    assert comparison.mean_difference == pytest.approx(-0.8)
    assert comparison.confidence_interval.lower == pytest.approx(-0.8)
    assert comparison.confidence_interval.upper == pytest.approx(-0.8)


def test_statistics_reject_invalid_inputs_and_unpaired_results() -> None:
    with pytest.raises(ValueError, match="at least one"):
        summarize((), resamples=100)
    with pytest.raises(ValueError, match="resamples"):
        summarize((1.0,), resamples=0)

    benchmark = PointMass2D(horizon=4)
    left = evaluate(
        OraclePointMassAdapter(benchmark),
        benchmark,
        benchmark.make_suite(contexts=4, seed=1),
    )
    right = evaluate(
        CopyLastFrameAdapter(),
        benchmark,
        benchmark.make_suite(contexts=3, seed=1),
    )
    with pytest.raises(ValueError, match="paired context"):
        paired_metric_comparison(left, right, metric="state_fde", resamples=100)
