"""Counterfactual, dynamics, and control-utility metrics."""

from __future__ import annotations

from itertools import combinations

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
