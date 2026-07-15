"""End-to-end counterfactual evaluation orchestration."""

from __future__ import annotations

import hashlib
import math
from dataclasses import asdict, dataclass
from typing import Any, cast

from wamprobe.api.model import WAMAdapter
from wamprobe.api.types import Context2D, InterventionSuite, Trajectory2D
from wamprobe.benchmarks.pointmass import PointMass2D
from wamprobe.metrics import (
    action_dependence,
    action_dependence_permutation_test,
    candidate_ranking_correlation,
    counterfactual_direction_accuracy,
    noop_stability,
    state_ade,
    state_fde,
)


@dataclass(frozen=True, slots=True)
class ContextResult:
    """Candidate-selection result for one shared initial state."""

    context_id: str
    selected_action: str
    optimal_action: str
    top1_regret: float
    metrics: dict[str, float]


@dataclass(frozen=True, slots=True)
class EvaluationResult:
    """Aggregated metrics and context-level control decisions."""

    model_id: str
    benchmark: str
    contexts: int
    metrics: dict[str, float]
    context_results: tuple[ContextResult, ...]

    def to_dict(self) -> dict[str, Any]:
        """Return a stable JSON-compatible result."""

        return {
            "schema_version": "0.1",
            "model_id": self.model_id,
            "benchmark": self.benchmark,
            "contexts": self.contexts,
            "metrics": self.metrics,
            "context_results": [asdict(result) for result in self.context_results],
        }

    @classmethod
    def from_dict(cls, value: object) -> EvaluationResult:
        """Strictly restore a versioned result from JSON-compatible data."""

        if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
            raise ValueError("evaluation result must be an object")
        payload = cast(dict[str, object], value)
        expected_fields = {
            "schema_version",
            "model_id",
            "benchmark",
            "contexts",
            "metrics",
            "context_results",
        }
        if payload.keys() != expected_fields:
            raise ValueError("evaluation result fields do not match schema 0.1")
        if payload["schema_version"] != "0.1":
            raise ValueError("unsupported evaluation result schema_version")
        model_id = _non_empty_string(payload["model_id"], "model_id")
        benchmark = _non_empty_string(payload["benchmark"], "benchmark")
        contexts = payload["contexts"]
        if isinstance(contexts, bool) or not isinstance(contexts, int) or contexts <= 0:
            raise ValueError("contexts must be a positive integer")
        metrics = _metric_mapping(payload["metrics"], "metrics")
        raw_contexts = payload["context_results"]
        if not isinstance(raw_contexts, list):
            raise ValueError("context_results must be an array")
        context_results = tuple(
            _context_result(raw, index) for index, raw in enumerate(raw_contexts)
        )
        if len(context_results) != contexts:
            raise ValueError("contexts does not match context_results length")
        context_ids = [result.context_id for result in context_results]
        if len(context_ids) != len(set(context_ids)):
            raise ValueError("context_result IDs must be unique")
        if any(result.metrics.keys() != metrics.keys() for result in context_results):
            raise ValueError("aggregated and context metric names must match")
        return cls(
            model_id=model_id,
            benchmark=benchmark,
            contexts=contexts,
            metrics=metrics,
            context_results=context_results,
        )


def _non_empty_string(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value


def _finite_float(value: object, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be a finite number")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{field} must be a finite number")
    return result


def _metric_mapping(value: object, field: str) -> dict[str, float]:
    if not isinstance(value, dict) or not value:
        raise ValueError(f"{field} must be a non-empty object")
    result: dict[str, float] = {}
    for key, metric_value in value.items():
        if not isinstance(key, str) or not key.strip():
            raise ValueError(f"{field} keys must be non-empty strings")
        result[key] = _finite_float(metric_value, f"{field}.{key}")
    return result


def _context_result(value: object, index: int) -> ContextResult:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise ValueError(f"context_results[{index}] must be an object")
    payload = cast(dict[str, object], value)
    expected = {
        "context_id",
        "selected_action",
        "optimal_action",
        "top1_regret",
        "metrics",
    }
    if payload.keys() != expected:
        raise ValueError(f"context_results[{index}] fields do not match schema")
    top1_regret = _finite_float(payload["top1_regret"], "top1_regret")
    metrics = _metric_mapping(payload["metrics"], "context metrics")
    if "top1_regret" in metrics and not math.isclose(
        metrics["top1_regret"], top1_regret, rel_tol=0.0, abs_tol=1e-12
    ):
        raise ValueError("context top1_regret does not match metrics")
    return ContextResult(
        context_id=_non_empty_string(payload["context_id"], "context_id"),
        selected_action=_non_empty_string(payload["selected_action"], "selected_action"),
        optimal_action=_non_empty_string(payload["optimal_action"], "optimal_action"),
        top1_regret=top1_regret,
        metrics=metrics,
    )


def evaluate(
    adapter: WAMAdapter,
    benchmark: PointMass2D,
    suite: InterventionSuite,
    *,
    seed: int = 0,
) -> EvaluationResult:
    """Evaluate one adapter on paired point-mass interventions."""

    if suite.benchmark_id != benchmark.benchmark_id:
        raise ValueError("suite and benchmark IDs must match")

    context_results: list[ContextResult] = []
    for group in suite.groups:
        samples: list[tuple[Context2D, Trajectory2D, Trajectory2D]] = []
        predicted_scores: dict[str, float] = {}
        true_scores: dict[str, float] = {}
        for action in group.actions:
            truth = benchmark.rollout(group.context, action)
            predicted = adapter.predict_future(
                group.context,
                action,
                horizon=benchmark.horizon,
                seed=seed,
            )
            if predicted.context_id != group.context.context_id:
                raise ValueError("adapter returned a mismatched context_id")
            if predicted.action_name != action.name:
                raise ValueError("adapter returned a mismatched action_name")
            samples.append((group.context, predicted, truth))
            predicted_scores[action.name] = benchmark.score(group.context, predicted)
            true_scores[action.name] = benchmark.score(group.context, truth)

        selected = max(predicted_scores, key=predicted_scores.__getitem__)
        optimal = max(true_scores, key=true_scores.__getitem__)
        regret = true_scores[optimal] - true_scores[selected]
        permutation_seed = int.from_bytes(
            hashlib.sha256(f"{seed}\0{group.context.context_id}".encode()).digest()[:8],
            "big",
        )
        permutation_result = action_dependence_permutation_test(
            samples,
            permutations=128,
            seed=permutation_seed,
        )
        ranking_result = candidate_ranking_correlation(predicted_scores, true_scores)
        context_metrics = {
            "action_dependence": action_dependence([samples]),
            "action_dependence_permutation_effect": permutation_result.effect_size,
            "action_dependence_permutation_p_value": permutation_result.p_value,
            "counterfactual_direction_accuracy": counterfactual_direction_accuracy(samples),
            "noop_stability": noop_stability(samples),
            "state_ade": state_ade(samples),
            "state_fde": state_fde(samples),
            "candidate_ranking_spearman": ranking_result.spearman,
            "candidate_ranking_kendall_tau": ranking_result.kendall_tau,
            "candidate_ranking_ndcg": ranking_result.ndcg,
            "candidate_ranking_pairwise_accuracy": (ranking_result.pairwise_preference_accuracy),
            "top1_regret": regret,
        }
        context_results.append(
            ContextResult(
                context_id=group.context.context_id,
                selected_action=selected,
                optimal_action=optimal,
                top1_regret=regret,
                metrics=context_metrics,
            )
        )
    metric_names = context_results[0].metrics.keys()
    metrics = {
        metric: sum(result.metrics[metric] for result in context_results) / len(context_results)
        for metric in metric_names
    }
    adapter.close()
    return EvaluationResult(
        model_id=adapter.capabilities.model_id,
        benchmark=benchmark.benchmark_id,
        contexts=len(suite.groups),
        metrics=metrics,
        context_results=tuple(context_results),
    )
