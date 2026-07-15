"""Dependency-free context-block statistics for paired WAM evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from random import Random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

    from wamprobe.evaluation import EvaluationResult


@dataclass(frozen=True, slots=True)
class ConfidenceInterval:
    """Percentile bootstrap interval whose resampling unit is one context."""

    estimate: float
    lower: float
    upper: float
    confidence_level: float
    resamples: int
    unit: str = "context"


@dataclass(frozen=True, slots=True)
class MetricSummary:
    """Descriptive statistics and a context-block confidence interval."""

    mean: float
    median: float
    standard_deviation: float
    quantiles: dict[str, float]
    confidence_interval: ConfidenceInterval
    contexts: int


@dataclass(frozen=True, slots=True)
class PairedComparison:
    """Paired left-minus-right metric difference over shared contexts."""

    metric: str
    left_model: str
    right_model: str
    contexts: int
    mean_difference: float
    confidence_interval: ConfidenceInterval


def _mean(values: Sequence[float]) -> float:
    return sum(values) / len(values)


def _quantile(sorted_values: Sequence[float], probability: float) -> float:
    if not 0.0 <= probability <= 1.0:
        raise ValueError("quantile probability must be in [0, 1]")
    if len(sorted_values) == 1:
        return sorted_values[0]
    position = probability * (len(sorted_values) - 1)
    lower_index = int(position)
    upper_index = min(lower_index + 1, len(sorted_values) - 1)
    fraction = position - lower_index
    return sorted_values[lower_index] * (1.0 - fraction) + sorted_values[upper_index] * fraction


def _bootstrap_interval(
    values: Sequence[float],
    *,
    resamples: int,
    seed: int,
    confidence_level: float,
) -> ConfidenceInterval:
    if resamples <= 0:
        raise ValueError("resamples must be positive")
    if not 0.0 < confidence_level < 1.0:
        raise ValueError("confidence_level must be between zero and one")

    rng = Random(seed)
    count = len(values)
    bootstrap_means = sorted(
        _mean([values[rng.randrange(count)] for _ in range(count)]) for _ in range(resamples)
    )
    tail = (1.0 - confidence_level) / 2.0
    return ConfidenceInterval(
        estimate=_mean(values),
        lower=_quantile(bootstrap_means, tail),
        upper=_quantile(bootstrap_means, 1.0 - tail),
        confidence_level=confidence_level,
        resamples=resamples,
    )


def summarize(
    values: Sequence[float],
    *,
    resamples: int = 1000,
    seed: int = 0,
    confidence_level: float = 0.95,
) -> MetricSummary:
    """Summarize context scores without treating branches or frames as independent."""

    if not values:
        raise ValueError("at least one context value is required")
    if resamples <= 0:
        raise ValueError("resamples must be positive")
    ordered = sorted(float(value) for value in values)
    mean = _mean(ordered)
    standard_deviation = sqrt(sum((value - mean) ** 2 for value in ordered) / len(ordered))
    quantiles = {
        "p05": _quantile(ordered, 0.05),
        "p25": _quantile(ordered, 0.25),
        "p75": _quantile(ordered, 0.75),
        "p95": _quantile(ordered, 0.95),
    }
    return MetricSummary(
        mean=mean,
        median=_quantile(ordered, 0.5),
        standard_deviation=standard_deviation,
        quantiles=quantiles,
        confidence_interval=_bootstrap_interval(
            ordered,
            resamples=resamples,
            seed=seed,
            confidence_level=confidence_level,
        ),
        contexts=len(ordered),
    )


def paired_metric_comparison(
    left: EvaluationResult,
    right: EvaluationResult,
    *,
    metric: str,
    resamples: int = 1000,
    seed: int = 0,
    confidence_level: float = 0.95,
) -> PairedComparison:
    """Bootstrap paired per-context differences after exact context-ID alignment."""

    if left.benchmark != right.benchmark:
        raise ValueError("paired results must use the same benchmark")

    left_values = {result.context_id: result.metrics for result in left.context_results}
    right_values = {result.context_id: result.metrics for result in right.context_results}
    if len(left_values) != len(left.context_results) or len(right_values) != len(
        right.context_results
    ):
        raise ValueError("paired context IDs must be unique")
    if left_values.keys() != right_values.keys():
        raise ValueError("paired context IDs must match exactly")

    differences: list[float] = []
    for context_id in sorted(left_values):
        if metric not in left_values[context_id] or metric not in right_values[context_id]:
            raise ValueError(f"metric is unavailable for paired context: {metric}")
        differences.append(left_values[context_id][metric] - right_values[context_id][metric])
    interval = _bootstrap_interval(
        differences,
        resamples=resamples,
        seed=seed,
        confidence_level=confidence_level,
    )
    return PairedComparison(
        metric=metric,
        left_model=left.model_id,
        right_model=right.model_id,
        contexts=len(differences),
        mean_difference=interval.estimate,
        confidence_interval=interval,
    )
