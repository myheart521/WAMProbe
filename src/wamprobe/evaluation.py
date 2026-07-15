"""End-to-end counterfactual evaluation orchestration."""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from typing import Any

from wamprobe.api.model import WAMAdapter
from wamprobe.api.types import Context2D, InterventionSuite, Trajectory2D
from wamprobe.benchmarks.pointmass import PointMass2D
from wamprobe.metrics import (
    action_dependence,
    action_dependence_permutation_test,
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
        context_metrics = {
            "action_dependence": action_dependence([samples]),
            "action_dependence_permutation_effect": permutation_result.effect_size,
            "action_dependence_permutation_p_value": permutation_result.p_value,
            "counterfactual_direction_accuracy": counterfactual_direction_accuracy(samples),
            "noop_stability": noop_stability(samples),
            "state_ade": state_ade(samples),
            "state_fde": state_fde(samples),
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
