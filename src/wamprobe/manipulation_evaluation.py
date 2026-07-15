"""Counterfactual evaluation for analytic manipulation state trajectories."""

from __future__ import annotations

import hashlib
from itertools import combinations
from math import sqrt

from wamprobe.api.manipulation import (
    ManipulationAdapter,
    ManipulationBenchmark,
    ManipulationContext,
    ManipulationInterventionSuite,
    ManipulationTrajectory,
)
from wamprobe.evaluation import ContextResult, EvaluationResult
from wamprobe.metrics import (
    action_dependence_permutation_vectors,
    candidate_ranking_correlation,
)

ManipulationSample = tuple[
    ManipulationContext,
    ManipulationTrajectory,
    ManipulationTrajectory,
]


def _distance(left: tuple[float, ...], right: tuple[float, ...]) -> float:
    if len(left) != len(right):
        raise ValueError("manipulation state vectors must have equal dimensions")
    return sqrt(
        sum(
            (left_value - right_value) ** 2
            for left_value, right_value in zip(left, right, strict=True)
        )
    )


def _displacement(start: tuple[float, ...], end: tuple[float, ...]) -> tuple[float, ...]:
    return tuple(end_value - start_value for start_value, end_value in zip(start, end, strict=True))


def _dot(left: tuple[float, ...], right: tuple[float, ...]) -> float:
    return sum(
        left_value * right_value for left_value, right_value in zip(left, right, strict=True)
    )


def _state_errors(samples: list[ManipulationSample]) -> tuple[float, float]:
    step_errors: list[float] = []
    final_errors: list[float] = []
    for _, predicted, truth in samples:
        if len(predicted.states) != len(truth.states):
            raise ValueError("predicted and true trajectories must have equal horizons")
        errors = [
            _distance(predicted_state.vector(), true_state.vector())
            for predicted_state, true_state in zip(predicted.states, truth.states, strict=True)
        ]
        step_errors.extend(errors)
        final_errors.append(errors[-1])
    return sum(step_errors) / len(step_errors), sum(final_errors) / len(final_errors)


def _counterfactual_direction(samples: list[ManipulationSample]) -> float:
    scores: list[float] = []
    for context, predicted, truth in samples:
        start = context.initial_state.vector()
        predicted_delta = _displacement(start, predicted.final_state.vector())
        truth_delta = _displacement(start, truth.final_state.vector())
        truth_norm = sqrt(_dot(truth_delta, truth_delta))
        if truth_norm <= 1e-12:
            continue
        predicted_norm = sqrt(_dot(predicted_delta, predicted_delta))
        if predicted_norm <= 1e-12:
            scores.append(0.0)
            continue
        scores.append(_dot(predicted_delta, truth_delta) / (predicted_norm * truth_norm))
    return sum(scores) / len(scores) if scores else 0.0


def _action_dependence(samples: list[ManipulationSample]) -> float:
    predicted_endpoints = [predicted.final_state.vector() for _, predicted, _ in samples]
    truth_endpoints = [truth.final_state.vector() for _, _, truth in samples]
    predicted_distances = [
        _distance(predicted_endpoints[left], predicted_endpoints[right])
        for left, right in combinations(range(len(samples)), 2)
    ]
    truth_distances = [
        _distance(truth_endpoints[left], truth_endpoints[right])
        for left, right in combinations(range(len(samples)), 2)
    ]
    predicted_mean = sum(predicted_distances) / len(predicted_distances)
    truth_mean = sum(truth_distances) / len(truth_distances)
    return min(1.0, predicted_mean / truth_mean) if truth_mean > 1e-15 else 0.0


def _noop_fidelity(samples: list[ManipulationSample]) -> float:
    noop_scores = [
        1.0
        if _distance(predicted.final_state.vector(), truth.final_state.vector()) <= 1e-12
        else 0.0
        for _, predicted, truth in samples
        if truth.action_name == "noop"
    ]
    return sum(noop_scores) / len(noop_scores) if noop_scores else 0.0


def evaluate_manipulation(
    adapter: ManipulationAdapter,
    benchmark: ManipulationBenchmark,
    suite: ManipulationInterventionSuite,
    *,
    seed: int = 0,
) -> EvaluationResult:
    """Evaluate one adapter over paired contact/grasp intervention groups."""

    if suite.benchmark_id != benchmark.benchmark_id:
        raise ValueError("suite and benchmark IDs must match")

    context_results: list[ContextResult] = []
    try:
        for group in suite.groups:
            samples: list[ManipulationSample] = []
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
            permutation_result = action_dependence_permutation_vectors(
                predicted_endpoints=[predicted.final_state.vector() for _, predicted, _ in samples],
                truth_endpoints=[truth.final_state.vector() for _, _, truth in samples],
                permutations=128,
                seed=permutation_seed,
            )
            ranking_result = candidate_ranking_correlation(predicted_scores, true_scores)
            state_ade, state_fde = _state_errors(samples)
            context_metrics = {
                "action_dependence": _action_dependence(samples),
                "action_dependence_permutation_effect": permutation_result.effect_size,
                "action_dependence_permutation_p_value": permutation_result.p_value,
                "counterfactual_direction_accuracy": _counterfactual_direction(samples),
                "noop_stability": _noop_fidelity(samples),
                "state_ade": state_ade,
                "state_fde": state_fde,
                "candidate_ranking_spearman": ranking_result.spearman,
                "candidate_ranking_kendall_tau": ranking_result.kendall_tau,
                "candidate_ranking_ndcg": ranking_result.ndcg,
                "candidate_ranking_pairwise_accuracy": (
                    ranking_result.pairwise_preference_accuracy
                ),
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
    finally:
        adapter.close()

    metric_names = context_results[0].metrics.keys()
    metrics = {
        metric: sum(result.metrics[metric] for result in context_results) / len(context_results)
        for metric in metric_names
    }
    return EvaluationResult(
        model_id=adapter.capabilities.model_id,
        benchmark=benchmark.benchmark_id,
        contexts=len(suite.groups),
        metrics=metrics,
        context_results=tuple(context_results),
    )
