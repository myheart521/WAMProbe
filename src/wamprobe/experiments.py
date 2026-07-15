"""Analysis and reporting for cached real-model action execution matrices."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass
from itertools import combinations
from pathlib import Path
from typing import cast


def _mapping(value: object, field: str) -> dict[str, object]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise ValueError(f"{field} must be an object")
    return cast(dict[str, object], value)


def _list(value: object, field: str) -> list[object]:
    if not isinstance(value, list):
        raise ValueError(f"{field} must be an array")
    return cast(list[object], value)


def _string(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value


def _integer(value: object, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field} must be an integer")
    return value


def _number(value: object, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be a finite number")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{field} must be a finite number")
    return result


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(8 * 1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def _read_json(path: Path, field: str) -> dict[str, object]:
    try:
        raw: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError(f"could not read {field}: {error}") from error
    return _mapping(raw, field)


@dataclass(frozen=True, slots=True)
class ActionExperimentRecord:
    """One predicted action chunk and its simulator prefix outcomes."""

    task_key: str
    seed: int
    num_inference_steps: int
    cache_key: str
    actions: tuple[tuple[float, ...], ...]
    latency_seconds: float
    peak_allocated_bytes: int
    initial_eef_position: tuple[float, float, float]
    final_eef_positions: dict[int, tuple[float, float, float]]
    cumulative_returns: dict[int, float]
    successes: dict[int, bool]

    @property
    def action_rms(self) -> float:
        """Root-mean-square command magnitude over the complete chunk."""

        values = [value for action in self.actions for value in action]
        return math.sqrt(sum(value * value for value in values) / len(values))

    @property
    def action_smoothness(self) -> float:
        """Mean L2 command change between consecutive steps; lower is smoother."""

        changes = [
            math.dist(left, right)
            for left, right in zip(self.actions, self.actions[1:], strict=False)
        ]
        return sum(changes) / len(changes)


@dataclass(frozen=True, slots=True)
class EfficiencySummary:
    """Runtime, memory, and command statistics for one NFE setting."""

    num_inference_steps: int
    samples: int
    mean_latency_seconds: float
    mean_peak_allocated_gib: float
    mean_action_rms: float
    mean_action_smoothness: float


@dataclass(frozen=True, slots=True)
class HorizonSummary:
    """Real simulator outcomes at one executed action prefix."""

    horizon: int
    samples: int
    success_rate: float
    mean_cumulative_return: float
    mean_eef_displacement: float


@dataclass(frozen=True, slots=True)
class SensitivitySummary:
    """Paired output variability along one experimental axis."""

    axis: str
    groups: int
    pairs: int
    mean_action_rms_difference: float
    mean_final_eef_distance: dict[int, float]


@dataclass(frozen=True, slots=True)
class ActionExperimentAnalysis:
    """Complete metric profile for a StarWAM inference/execution matrix."""

    model_id: str
    benchmark_id: str
    predictions: int
    failed_predictions: int
    executions: int
    failed_execution_tasks: int
    efficiency: tuple[EfficiencySummary, ...]
    horizons: tuple[HorizonSummary, ...]
    seed_sensitivity: SensitivitySummary
    nfe_sensitivity: SensitivitySummary
    correlations: dict[str, float | None]
    skipped_analyses: tuple[dict[str, str], ...]
    matrix_sha256: str
    execution_sha256: str
    schema_version: str = "0.1"

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-compatible experiment report."""

        return {
            "schema_version": self.schema_version,
            "model_id": self.model_id,
            "benchmark_id": self.benchmark_id,
            "predictions": self.predictions,
            "failed_predictions": self.failed_predictions,
            "prediction_failure_rate": self.failed_predictions
            / max(self.predictions + self.failed_predictions, 1),
            "executions": self.executions,
            "failed_execution_tasks": self.failed_execution_tasks,
            "efficiency": [asdict(summary) for summary in self.efficiency],
            "horizons": [asdict(summary) for summary in self.horizons],
            "seed_sensitivity": asdict(self.seed_sensitivity),
            "nfe_sensitivity": asdict(self.nfe_sensitivity),
            "correlations": self.correlations,
            "skipped_analyses": list(self.skipped_analyses),
            "matrix_sha256": self.matrix_sha256,
            "execution_sha256": self.execution_sha256,
        }


def _action_chunk(value: object) -> tuple[tuple[float, ...], ...]:
    actions: list[tuple[float, ...]] = []
    for action_index, raw_action in enumerate(_list(value, "prediction.actions")):
        action = tuple(
            _number(item, f"prediction.actions[{action_index}]")
            for item in _list(raw_action, f"prediction.actions[{action_index}]")
        )
        if not action:
            raise ValueError("prediction actions must not be empty")
        actions.append(action)
    if len(actions) < 2 or len({len(action) for action in actions}) != 1:
        raise ValueError("prediction action chunk must have a stable non-empty shape")
    return tuple(actions)


def _vec3(value: object, field: str) -> tuple[float, float, float]:
    items = _list(value, field)
    if len(items) != 3:
        raise ValueError(f"{field} must contain three coordinates")
    return (
        _number(items[0], field),
        _number(items[1], field),
        _number(items[2], field),
    )


def load_action_experiment(
    matrix_path: Path,
    execution_path: Path,
) -> tuple[dict[str, object], dict[str, object], tuple[ActionExperimentRecord, ...]]:
    """Strictly align cached predictions and executed outcomes by cache key."""

    matrix = _read_json(matrix_path, "matrix index")
    execution = _read_json(execution_path, "execution index")
    matrix_records = _list(matrix.get("records"), "matrix records")
    execution_records = _list(execution.get("records"), "execution records")
    execution_by_key: dict[str, dict[str, object]] = {}
    for index, raw_record in enumerate(execution_records):
        record = _mapping(raw_record, f"execution records[{index}]")
        key = _string(record.get("cache_key"), "execution cache_key")
        if key in execution_by_key:
            raise ValueError(f"duplicate execution cache_key: {key}")
        execution_by_key[key] = record

    records: list[ActionExperimentRecord] = []
    for index, raw_matrix_record in enumerate(matrix_records):
        matrix_record = _mapping(raw_matrix_record, f"matrix records[{index}]")
        status = _string(matrix_record.get("status"), "matrix status")
        if status not in {"generated", "cache-hit"}:
            continue
        cache_key = _string(matrix_record.get("cache_key"), "matrix cache_key")
        execution_record = execution_by_key.pop(cache_key, None)
        if execution_record is None:
            raise ValueError(f"missing execution for cache_key: {cache_key}")
        prediction_path = matrix_path.parent / "predictions" / f"{cache_key}.json"
        prediction_artifact = _read_json(prediction_path, "prediction artifact")
        if prediction_artifact.get("cache_key") != cache_key:
            raise ValueError("prediction artifact cache_key mismatch")
        prediction = _mapping(prediction_artifact.get("prediction"), "prediction")
        runtime = _mapping(prediction.get("runtime"), "prediction.runtime")
        outcome = _mapping(execution_record.get("outcome"), "execution outcome")
        checkpoints = _mapping(outcome.get("checkpoints"), "outcome.checkpoints")
        final_positions: dict[int, tuple[float, float, float]] = {}
        returns: dict[int, float] = {}
        successes: dict[int, bool] = {}
        for raw_horizon, raw_checkpoint in checkpoints.items():
            try:
                horizon = int(raw_horizon)
            except ValueError as error:
                raise ValueError("checkpoint horizon must be an integer string") from error
            checkpoint = _mapping(raw_checkpoint, f"checkpoint {horizon}")
            final_positions[horizon] = _vec3(
                checkpoint.get("eef_position"),
                f"checkpoint {horizon} eef_position",
            )
            returns[horizon] = _number(
                checkpoint.get("cumulative_return"),
                f"checkpoint {horizon} cumulative_return",
            )
            success = checkpoint.get("success")
            if not isinstance(success, bool):
                raise ValueError(f"checkpoint {horizon} success must be boolean")
            successes[horizon] = success
        records.append(
            ActionExperimentRecord(
                task_key=_string(matrix_record.get("task_key"), "task_key"),
                seed=_integer(matrix_record.get("seed"), "seed"),
                num_inference_steps=_integer(
                    matrix_record.get("num_inference_steps"),
                    "num_inference_steps",
                ),
                cache_key=cache_key,
                actions=_action_chunk(prediction.get("actions")),
                latency_seconds=_number(
                    runtime.get("latency_seconds"),
                    "runtime.latency_seconds",
                ),
                peak_allocated_bytes=_integer(
                    runtime.get("peak_allocated_bytes"),
                    "runtime.peak_allocated_bytes",
                ),
                initial_eef_position=_vec3(
                    outcome.get("initial_eef_position"),
                    "initial_eef_position",
                ),
                final_eef_positions=final_positions,
                cumulative_returns=returns,
                successes=successes,
            )
        )
    if execution_by_key:
        raise ValueError("execution index contains outcomes without matrix predictions")
    if not records:
        raise ValueError("experiment contains no aligned completed records")
    configuration_keys = [
        (record.task_key, record.seed, record.num_inference_steps) for record in records
    ]
    if len(configuration_keys) != len(set(configuration_keys)):
        raise ValueError("experiment task/seed/NFE configurations must be unique")
    return matrix, execution, tuple(records)


def _mean(values: list[float]) -> float:
    if not values:
        raise ValueError("cannot average an empty collection")
    return sum(values) / len(values)


def _pair_action_rms(
    left: ActionExperimentRecord,
    right: ActionExperimentRecord,
) -> float:
    if len(left.actions) != len(right.actions) or any(
        len(left_action) != len(right_action)
        for left_action, right_action in zip(left.actions, right.actions, strict=True)
    ):
        raise ValueError("paired action chunks must have equal shapes")
    differences = [
        left_value - right_value
        for left_action, right_action in zip(left.actions, right.actions, strict=True)
        for left_value, right_value in zip(left_action, right_action, strict=True)
    ]
    return math.sqrt(sum(value * value for value in differences) / len(differences))


def _sensitivity(
    records: tuple[ActionExperimentRecord, ...],
    *,
    axis: str,
    group_key: str,
) -> SensitivitySummary:
    grouped: dict[tuple[str, int], list[ActionExperimentRecord]] = {}
    for record in records:
        varying_value = record.num_inference_steps if group_key == "nfe" else record.seed
        grouped.setdefault((record.task_key, varying_value), []).append(record)
    action_differences: list[float] = []
    endpoint_differences: dict[int, list[float]] = {}
    pair_count = 0
    for values in grouped.values():
        for left, right in combinations(values, 2):
            pair_count += 1
            action_differences.append(_pair_action_rms(left, right))
            if left.final_eef_positions.keys() != right.final_eef_positions.keys():
                raise ValueError("paired execution horizons must match")
            for horizon in left.final_eef_positions:
                endpoint_differences.setdefault(horizon, []).append(
                    math.dist(
                        left.final_eef_positions[horizon],
                        right.final_eef_positions[horizon],
                    )
                )
    return SensitivitySummary(
        axis=axis,
        groups=len(grouped),
        pairs=pair_count,
        mean_action_rms_difference=_mean(action_differences),
        mean_final_eef_distance={
            horizon: _mean(values) for horizon, values in sorted(endpoint_differences.items())
        },
    )


def _pearson(left: list[float], right: list[float]) -> float | None:
    if len(left) != len(right) or len(left) < 2:
        raise ValueError("correlation inputs must have matching lengths of at least two")
    left_mean = _mean(left)
    right_mean = _mean(right)
    left_delta = [value - left_mean for value in left]
    right_delta = [value - right_mean for value in right]
    denominator = math.sqrt(
        sum(value * value for value in left_delta) * sum(value * value for value in right_delta)
    )
    if denominator <= 1e-15:
        return None
    return (
        sum(
            left_value * right_value
            for left_value, right_value in zip(left_delta, right_delta, strict=True)
        )
        / denominator
    )


def analyze_action_experiment(
    matrix_path: Path,
    execution_path: Path,
) -> ActionExperimentAnalysis:
    """Compute efficiency, stability, and real control-outcome profiles."""

    matrix, execution, records = load_action_experiment(matrix_path, execution_path)
    nfe_values = sorted({record.num_inference_steps for record in records})
    efficiency = tuple(
        EfficiencySummary(
            num_inference_steps=nfe,
            samples=len(selected),
            mean_latency_seconds=_mean([record.latency_seconds for record in selected]),
            mean_peak_allocated_gib=_mean(
                [record.peak_allocated_bytes / 1024**3 for record in selected]
            ),
            mean_action_rms=_mean([record.action_rms for record in selected]),
            mean_action_smoothness=_mean([record.action_smoothness for record in selected]),
        )
        for nfe in nfe_values
        if (selected := [record for record in records if record.num_inference_steps == nfe])
    )
    horizon_values = sorted(records[0].final_eef_positions)
    if any(sorted(record.final_eef_positions) != horizon_values for record in records):
        raise ValueError("all execution records must share horizon checkpoints")
    horizons = tuple(
        HorizonSummary(
            horizon=horizon,
            samples=len(records),
            success_rate=_mean([float(record.successes[horizon]) for record in records]),
            mean_cumulative_return=_mean(
                [record.cumulative_returns[horizon] for record in records]
            ),
            mean_eef_displacement=_mean(
                [
                    math.dist(
                        record.initial_eef_position,
                        record.final_eef_positions[horizon],
                    )
                    for record in records
                ]
            ),
        )
        for horizon in horizon_values
    )
    correlations = {
        "nfe_vs_latency_pearson": _pearson(
            [float(record.num_inference_steps) for record in records],
            [record.latency_seconds for record in records],
        ),
        "nfe_vs_success_pearson": _pearson(
            [float(record.num_inference_steps) for record in records],
            [float(record.successes[horizon_values[-1]]) for record in records],
        ),
    }
    for horizon in horizon_values:
        displacements = [
            math.dist(
                record.initial_eef_position,
                record.final_eef_positions[horizon],
            )
            for record in records
        ]
        correlations[f"action_rms_vs_eef_displacement_h{horizon}_pearson"] = _pearson(
            [record.action_rms for record in records],
            displacements,
        )
        correlations[f"action_smoothness_vs_eef_displacement_h{horizon}_pearson"] = _pearson(
            [record.action_smoothness for record in records],
            displacements,
        )
    raw_skips = _list(matrix.get("capability_skips", []), "capability_skips")
    skipped = tuple(
        {
            "analysis": _string(
                _mapping(item, "capability skip").get("ablation"),
                "capability skip ablation",
            ),
            "reason": _string(
                _mapping(item, "capability skip").get("reason"),
                "capability skip reason",
            ),
        }
        for item in raw_skips
    ) + (
        {
            "analysis": "predicted-video-quality-vs-control",
            "reason": (
                "the released adapter exposes actions but no predicted video or future-state "
                "artifact, so PSNR/SSIM/FVD would be fabricated"
            ),
        },
        {
            "analysis": "success-correlation",
            "reason": (
                "all short-horizon fixed-context executions have zero sparse success and "
                "return, so the correlation is undefined"
            ),
        },
    )
    failed_execution_tasks = len(_list(execution.get("failed_tasks", []), "failed execution tasks"))
    return ActionExperimentAnalysis(
        model_id=_string(matrix.get("model_id"), "model_id"),
        benchmark_id=_string(matrix.get("benchmark_id"), "benchmark_id"),
        predictions=len(records),
        failed_predictions=_integer(
            matrix.get("failed_predictions", 0),
            "failed_predictions",
        ),
        executions=len(records),
        failed_execution_tasks=failed_execution_tasks,
        efficiency=efficiency,
        horizons=horizons,
        seed_sensitivity=_sensitivity(records, axis="seed", group_key="nfe"),
        nfe_sensitivity=_sensitivity(records, axis="nfe", group_key="seed"),
        correlations=correlations,
        skipped_analyses=skipped,
        matrix_sha256=_sha256_file(matrix_path),
        execution_sha256=_sha256_file(execution_path),
    )


def render_action_experiment_markdown(analysis: ActionExperimentAnalysis) -> str:
    """Render a compact human-readable experiment report."""

    lines = [
        "# WAMProbe StarWAM action experiment",
        "",
        f"- Model: `{analysis.model_id}`",
        f"- Benchmark: `{analysis.benchmark_id}`",
        f"- Predictions/executions: {analysis.predictions}/{analysis.executions}",
        f"- Failed predictions/tasks: {analysis.failed_predictions}/"
        f"{analysis.failed_execution_tasks}",
        "",
        "## Efficiency by NFE",
        "",
        "| NFE | Samples | Mean latency (s) | Peak GiB | Action RMS | Step change |",
        "|---:|---:|---:|---:|---:|---:|",
    ]
    for efficiency_summary in analysis.efficiency:
        lines.append(
            f"| {efficiency_summary.num_inference_steps} | "
            f"{efficiency_summary.samples} | "
            f"{efficiency_summary.mean_latency_seconds:.4f} | "
            f"{efficiency_summary.mean_peak_allocated_gib:.3f} | "
            f"{efficiency_summary.mean_action_rms:.4f} | "
            f"{efficiency_summary.mean_action_smoothness:.4f} |"
        )
    lines.extend(
        [
            "",
            "## Simulator outcomes",
            "",
            "| Horizon | Samples | Success | Mean return | Mean EEF displacement |",
            "|---:|---:|---:|---:|---:|",
        ]
    )
    for horizon_summary in analysis.horizons:
        lines.append(
            f"| {horizon_summary.horizon} | {horizon_summary.samples} | "
            f"{horizon_summary.success_rate:.4f} | "
            f"{horizon_summary.mean_cumulative_return:.4f} | "
            f"{horizon_summary.mean_eef_displacement:.4f} |"
        )
    lines.extend(
        [
            "",
            "## Sensitivity",
            "",
            f"- Seed action RMS difference: "
            f"{analysis.seed_sensitivity.mean_action_rms_difference:.6f}",
            f"- NFE action RMS difference: "
            f"{analysis.nfe_sensitivity.mean_action_rms_difference:.6f}",
            "",
            "## Capability-gated and undefined analyses",
            "",
        ]
    )
    lines.extend(f"- `{item['analysis']}`: {item['reason']}" for item in analysis.skipped_analyses)
    lines.extend(
        [
            "",
            "Zero sparse success is reported as a negative fixed-context result. It is not a",
            "LIBERO policy success-rate estimate and is not replaced by a composite score.",
            "",
        ]
    )
    return "\n".join(lines)


def write_action_experiment_report(
    output_dir: Path,
    analysis: ActionExperimentAnalysis,
) -> tuple[Path, Path]:
    """Write deterministic JSON and Markdown action-experiment reports."""

    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "experiment.json"
    markdown_path = output_dir / "experiment.md"
    json_path.write_text(
        json.dumps(analysis.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    markdown_path.write_text(
        render_action_experiment_markdown(analysis),
        encoding="utf-8",
    )
    return json_path, markdown_path
