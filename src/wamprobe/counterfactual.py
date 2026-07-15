"""Scoring and deterministic artifacts for paired robot interventions."""

from __future__ import annotations

import hashlib
import json
import math
import uuid
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path

from wamprobe.api.counterfactual import CounterfactualValidation, RobotInterventionGroup


@dataclass(frozen=True, slots=True)
class CounterfactualScores:
    """Small ground-truth branch-separation and control-outcome profile."""

    mean_final_eef_pairwise_distance: float
    mean_final_object_pairwise_distance: float
    noop_final_eef_drift: float | None
    return_spread: float
    success_rate: float

    def to_dict(self) -> dict[str, float | None]:
        """Return a JSON-compatible metric profile."""

        return {
            "mean_final_eef_pairwise_distance": self.mean_final_eef_pairwise_distance,
            "mean_final_object_pairwise_distance": self.mean_final_object_pairwise_distance,
            "noop_final_eef_drift": self.noop_final_eef_drift,
            "return_spread": self.return_spread,
            "success_rate": self.success_rate,
        }


def _mean(values: list[float]) -> float:
    return sum(values) / len(values)


def score_intervention_group(group: RobotInterventionGroup) -> CounterfactualScores:
    """Measure real branch separation, no-op drift, return spread, and success rate."""

    pairs = list(combinations(group.branches, 2))
    eef_distances = [
        math.dist(left.future.final_frame.eef_position, right.future.final_frame.eef_position)
        for left, right in pairs
    ]
    object_distances = [
        math.dist(left.future.final_frame.object_state, right.future.final_frame.object_state)
        for left, right in pairs
    ]
    noop_branches = [
        branch
        for branch in group.branches
        if branch.action_family == "no-op" or branch.branch_id == "noop"
    ]
    noop_drift = (
        math.dist(
            noop_branches[0].future.initial_frame.eef_position,
            noop_branches[0].future.final_frame.eef_position,
        )
        if noop_branches
        else None
    )
    returns = [branch.future.cumulative_return for branch in group.branches]
    return CounterfactualScores(
        mean_final_eef_pairwise_distance=_mean(eef_distances),
        mean_final_object_pairwise_distance=_mean(object_distances),
        noop_final_eef_drift=noop_drift,
        return_spread=max(returns) - min(returns),
        success_rate=_mean([float(branch.future.success) for branch in group.branches]),
    )


@dataclass(frozen=True, slots=True)
class CounterfactualArtifact:
    """One cacheable intervention group with real outcomes and restore validation."""

    group: RobotInterventionGroup
    validation: CounterfactualValidation
    schema_version: str = "0.1"

    def __post_init__(self) -> None:
        if self.schema_version != "0.1":
            raise ValueError(f"unsupported counterfactual artifact schema: {self.schema_version}")

    @property
    def metrics(self) -> CounterfactualScores:
        """Return the deterministic metric profile for the stored group."""

        return score_intervention_group(self.group)

    def _payload(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "group_sha256": self.group.content_sha256,
            "group": self.group.to_dict(),
            "metrics": self.metrics.to_dict(),
            "validation": self.validation.to_dict(),
        }

    @property
    def artifact_sha256(self) -> str:
        """Return a deterministic digest over group, scores, and validation."""

        encoded = json.dumps(
            self._payload(),
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def to_dict(self) -> dict[str, object]:
        """Return the complete JSON-compatible counterfactual artifact."""

        return {**self._payload(), "artifact_sha256": self.artifact_sha256}

    def write_json(self, path: Path) -> None:
        """Atomically write the lightweight artifact without raw state or image bytes."""

        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
        try:
            temporary.write_text(
                json.dumps(
                    self.to_dict(),
                    allow_nan=False,
                    indent=2,
                    ensure_ascii=False,
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)
