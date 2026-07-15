"""Counterfactual, dynamics, and control-utility metrics."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from itertools import permutations as generate_permutations
from math import factorial, sqrt
from random import Random

from wamprobe.api.types import Context2D, Trajectory2D, Vec2


def _displacement(context: Context2D, trajectory: Trajectory2D) -> Vec2:
    return trajectory.final_state - context.position


def counterfactual_direction_accuracy(
    samples: list[tuple[Context2D, Trajectory2D, Trajectory2D]],
) -> float:
    """Return mean cosine alignment between predicted and true non-noop displacements."""

    scores: list[float] = []
    for context, predicted, truth in samples:
        true_delta = _displacement(context, truth)
        if true_delta.norm() <= 1e-12:
            continue
        predicted_delta = _displacement(context, predicted)
        if predicted_delta.norm() <= 1e-12:
            scores.append(0.0)
            continue
        scores.append(
            predicted_delta.dot(true_delta) / (predicted_delta.norm() * true_delta.norm())
        )
    return sum(scores) / len(scores) if scores else 0.0


def state_ade(samples: list[tuple[Context2D, Trajectory2D, Trajectory2D]]) -> float:
    """Return average state displacement error over all branches and time steps."""

    errors: list[float] = []
    for _, predicted, truth in samples:
        if len(predicted.states) != len(truth.states):
            raise ValueError("predicted and true trajectories must have equal horizons")
        errors.extend(
            (predicted_state - true_state).norm()
            for predicted_state, true_state in zip(predicted.states, truth.states, strict=True)
        )
    return sum(errors) / len(errors) if errors else 0.0


def state_fde(samples: list[tuple[Context2D, Trajectory2D, Trajectory2D]]) -> float:
    """Return average final-state displacement error over all action branches."""

    errors: list[float] = []
    for _, predicted, truth in samples:
        if len(predicted.states) != len(truth.states):
            raise ValueError("predicted and true trajectories must have equal horizons")
        errors.append((predicted.final_state - truth.final_state).norm())
    return sum(errors) / len(errors) if errors else 0.0


@dataclass(frozen=True, slots=True)
class PermutationTestResult:
    """Action-dependence score relative to a context-local permutation null."""

    observed: float
    null_mean: float
    null_standard_deviation: float
    effect_size: float
    p_value: float
    permutations: int


def _pearson(left: list[float], right: list[float]) -> float:
    if len(left) != len(right):
        raise ValueError("correlation vectors must have equal lengths")
    if not left:
        return 0.0
    left_mean = sum(left) / len(left)
    right_mean = sum(right) / len(right)
    left_centered = [value - left_mean for value in left]
    right_centered = [value - right_mean for value in right]
    denominator = sqrt(
        sum(value * value for value in left_centered)
        * sum(value * value for value in right_centered)
    )
    if denominator <= 1e-15:
        return 0.0
    correlation = (
        sum(
            left_value * right_value
            for left_value, right_value in zip(left_centered, right_centered, strict=True)
        )
        / denominator
    )
    return max(-1.0, min(1.0, correlation))


def _pairwise_distances(states: list[Vec2]) -> list[float]:
    return [
        (states[left] - states[right]).norm() for left, right in combinations(range(len(states)), 2)
    ]


def _permutation_indices(size: int, *, count: int, seed: int) -> list[tuple[int, ...]]:
    identity = tuple(range(size))
    available = factorial(size) - 1
    if available <= count:
        return [
            permutation
            for permutation in generate_permutations(range(size))
            if permutation != identity
        ]

    rng = Random(seed)
    selected: set[tuple[int, ...]] = set()
    while len(selected) < count:
        candidate = list(identity)
        rng.shuffle(candidate)
        candidate_tuple = tuple(candidate)
        if candidate_tuple != identity:
            selected.add(candidate_tuple)
    return sorted(selected)


def action_dependence_permutation_test(
    samples: list[tuple[Context2D, Trajectory2D, Trajectory2D]],
    *,
    permutations: int = 128,
    seed: int = 0,
) -> PermutationTestResult:
    """Compare action/future geometry with a within-context permutation null.

    Ground-truth endpoint distances define the action-conditioned geometry. Predicted
    endpoints are reassigned to action labels to estimate how much alignment would be
    expected if the model's futures were unrelated to the supplied actions.
    """

    if len(samples) < 2:
        raise ValueError("permutation testing requires at least two action branches")
    if permutations <= 0:
        raise ValueError("permutations must be positive")
    context_ids = {context.context_id for context, _, _ in samples}
    if len(context_ids) != 1:
        raise ValueError("permutation samples must share one context")

    truth_distances = _pairwise_distances([truth.final_state for _, _, truth in samples])
    predicted_states = [predicted.final_state for _, predicted, _ in samples]
    observed = _pearson(truth_distances, _pairwise_distances(predicted_states))

    indices = _permutation_indices(len(samples), count=permutations, seed=seed)
    null_scores = [
        _pearson(
            truth_distances,
            _pairwise_distances([predicted_states[index] for index in permutation]),
        )
        for permutation in indices
    ]
    null_mean = sum(null_scores) / len(null_scores)
    null_variance = sum((score - null_mean) ** 2 for score in null_scores) / len(null_scores)
    null_standard_deviation = sqrt(null_variance)
    effect_size = (
        (observed - null_mean) / null_standard_deviation if null_standard_deviation > 1e-15 else 0.0
    )
    p_value = (1 + sum(score >= observed - 1e-15 for score in null_scores)) / (1 + len(null_scores))
    return PermutationTestResult(
        observed=observed,
        null_mean=null_mean,
        null_standard_deviation=null_standard_deviation,
        effect_size=effect_size,
        p_value=p_value,
        permutations=len(null_scores),
    )


def action_dependence(
    groups: list[list[tuple[Context2D, Trajectory2D, Trajectory2D]]],
) -> float:
    """Measure whether future endpoints separate when actions change.

    The score is a capped ratio of mean predicted pairwise endpoint distance to
    ground-truth pairwise endpoint distance. Direction correctness is intentionally
    evaluated separately by :func:`counterfactual_direction_accuracy`.
    """

    group_scores: list[float] = []
    for samples in groups:
        predicted_distances = [
            (left[1].final_state - right[1].final_state).norm()
            for left, right in combinations(samples, 2)
        ]
        true_distances = [
            (left[2].final_state - right[2].final_state).norm()
            for left, right in combinations(samples, 2)
        ]
        predicted_mean = sum(predicted_distances) / len(predicted_distances)
        true_mean = sum(true_distances) / len(true_distances)
        group_scores.append(min(1.0, predicted_mean / true_mean) if true_mean else 0.0)
    return sum(group_scores) / len(group_scores) if group_scores else 0.0


def noop_stability(
    samples: list[tuple[Context2D, Trajectory2D, Trajectory2D]],
) -> float:
    """Return the fraction of no-op predictions that remain at the current state."""

    noop_scores = [
        1.0 if _displacement(context, predicted).norm() <= 1e-12 else 0.0
        for context, predicted, truth in samples
        if truth.action_name == "noop"
    ]
    return sum(noop_scores) / len(noop_scores) if noop_scores else 0.0
