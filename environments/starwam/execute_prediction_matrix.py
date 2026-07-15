#!/usr/bin/env python
"""Execute cached StarWAM action chunks from pinned LIBERO-CF-Mini snapshots."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import uuid
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPOSITORY_ROOT / "src"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from environments.libero import generate_cf_pilot as cf  # noqa: E402
from wamprobe.libero_cf import LiberoTaskSpec, load_libero_cf_manifest  # noqa: E402

DEFAULT_MANIFEST = REPOSITORY_ROOT / "configs" / "benchmarks" / "libero_cf_mini_v0.1.json"
DEFAULT_MATRIX_DIR = REPOSITORY_ROOT / "runs" / "starwam-libero-cf-mini-v0.1"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(8 * 1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def _canonical_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        temporary.write_text(
            json.dumps(payload, allow_nan=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def _load_matrix(path: Path) -> dict[str, object]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise TypeError("matrix index must be an object")
    if raw.get("schema_version") != "0.1":
        raise ValueError("matrix index schema_version mismatch")
    records = raw.get("records")
    if not isinstance(records, list) or not records:
        raise ValueError("matrix index must contain prediction records")
    if raw.get("failed_predictions") != 0:
        raise ValueError("matrix index contains failed predictions")
    return raw


def _load_prediction(
    matrix_dir: Path,
    record: dict[str, object],
    spec: LiberoTaskSpec,
) -> tuple[list[list[float]], dict[str, object]]:
    cache_key = record.get("cache_key")
    if not isinstance(cache_key, str) or len(cache_key) != 64:
        raise ValueError("prediction record cache_key is invalid")
    path = matrix_dir / "predictions" / f"{cache_key}.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("cache_key") != cache_key:
        raise ValueError("prediction artifact cache_key mismatch")
    prediction = payload.get("prediction")
    observation = payload.get("observation")
    inference = payload.get("inference")
    if not all(isinstance(item, dict) for item in (prediction, observation, inference)):
        raise TypeError("prediction artifact sections must be objects")
    prediction = prediction  # keep the runtime-narrowed type visible to static readers
    observation = observation
    inference = inference
    if observation.get("context_id") != spec.context_id:
        raise ValueError("prediction observation context does not match task manifest")
    if prediction.get("context_id") != spec.context_id:
        raise ValueError("prediction context does not match task manifest")
    if prediction.get("seed") != record.get("seed"):
        raise ValueError("prediction seed does not match matrix index")
    if inference.get("num_inference_steps") != record.get("num_inference_steps"):
        raise ValueError("prediction NFE does not match matrix index")
    if payload.get("prediction_sha256") != _canonical_sha256(prediction):
        raise ValueError("prediction_sha256 mismatch")
    actions = prediction.get("actions")
    if not isinstance(actions, list) or len(actions) != 32:
        raise ValueError("prediction must contain a 32-step action chunk")
    parsed: list[list[float]] = []
    for action in actions:
        if not isinstance(action, list) or len(action) != 7:
            raise ValueError("prediction action shape must be [32, 7]")
        row: list[float] = []
        for value in action:
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(float(value))
            ):
                raise ValueError("prediction actions must be finite numbers")
            scalar = float(value)
            if not -1.0 <= scalar <= 1.0:
                raise ValueError("prediction actions must satisfy LIBERO [-1, 1] bounds")
            row.append(scalar)
        parsed.append(row)
    metadata = {
        "prediction_artifact": str(path),
        "prediction_artifact_sha256": _sha256_file(path),
        "prediction_sha256": payload["prediction_sha256"],
    }
    return parsed, metadata


def _execute_actions(
    environment: Any,
    snapshot: cf.RuntimeSnapshot,
    actions: list[list[float]],
    horizons: tuple[int, ...],
) -> dict[str, object]:
    import numpy as np

    observation = cf._restore_runtime_snapshot(environment, snapshot)
    initial_state_sha256 = cf._array_sha256(cf._integration_state(environment))
    cumulative_return = 0.0
    succeeded = bool(environment.check_success())
    done = bool(environment.env.done)
    checkpoints: dict[str, object] = {}
    for step_index, action in enumerate(actions[: max(horizons)], start=1):
        observation, reward, done, _ = environment.step(np.asarray(action, dtype=np.float64))
        cumulative_return += float(reward)
        succeeded = succeeded or bool(environment.check_success())
        if step_index in horizons:
            checkpoints[str(step_index)] = {
                "eef_position": [float(value) for value in observation["robot0_eef_pos"]],
                "object_state": [float(value) for value in observation["object-state"]],
                "cumulative_return": cumulative_return,
                "success": succeeded,
                "done": bool(done),
                "simulator_state_sha256": cf._array_sha256(cf._integration_state(environment)),
                "observation_sha256": cf._observation_sha256(observation),
            }
        if done:
            break
    return {
        "initial_state_sha256": initial_state_sha256,
        "initial_observation_sha256": cf._observation_sha256(observation),
        "initial_eef_position": [float(value) for value in observation["robot0_eef_pos"]],
        "initial_object_state": [float(value) for value in observation["object-state"]],
        "requested_horizons": list(horizons),
        "executed_steps": step_index,
        "terminated_early": step_index < max(horizons),
        "checkpoints": checkpoints,
    }


def _task_records(matrix: dict[str, object], task_key: str) -> list[dict[str, object]]:
    records = matrix["records"]
    if not isinstance(records, list):
        raise TypeError("matrix records must be an array")
    selected: list[dict[str, object]] = []
    for raw in records:
        if not isinstance(raw, dict):
            raise TypeError("matrix record must be an object")
        if raw.get("task_key") == task_key:
            if raw.get("status") not in {"generated", "cache-hit"}:
                raise ValueError("matrix record is not a completed prediction")
            selected.append(raw)
    if not selected:
        raise ValueError(f"matrix has no predictions for task: {task_key}")
    selected.sort(
        key=lambda record: (
            int(record["num_inference_steps"]),
            int(record["seed"]),
        )
    )
    return selected


def _run_task(
    matrix_dir: Path,
    matrix: dict[str, object],
    spec: LiberoTaskSpec,
    horizons: tuple[int, ...],
    *,
    libero_revision: str,
    benchmark_id: str,
) -> tuple[list[dict[str, object]], dict[str, object]]:
    task_run_dir = matrix_dir / "executions" / spec.key
    environment, init_states, _ = cf._prepare_environment(
        task_run_dir,
        spec,
        expected_libero_revision=libero_revision,
        benchmark_id=benchmark_id,
    )
    records: list[dict[str, object]] = []
    repeatability: dict[str, object] = {}
    try:
        environment.reset()
        environment.set_init_state(init_states[spec.init_state_index])
        for _ in range(spec.wait_steps):
            environment.step(cf.DUMMY_ACTION)
        snapshot = cf._capture_runtime_snapshot(environment)
        snapshot_state_sha256 = cf._array_sha256(snapshot.integration_state)

        for index, prediction_record in enumerate(_task_records(matrix, spec.key)):
            actions, metadata = _load_prediction(matrix_dir, prediction_record, spec)
            outcome = _execute_actions(environment, snapshot, actions, horizons)
            record = {
                "task_key": spec.key,
                "task_family": spec.task_family,
                "context_id": spec.context_id,
                "seed": prediction_record["seed"],
                "num_inference_steps": prediction_record["num_inference_steps"],
                "cache_key": prediction_record["cache_key"],
                "action_abs_max": max(abs(value) for action in actions for value in action),
                "snapshot_state_sha256": snapshot_state_sha256,
                **metadata,
                "outcome": outcome,
                "status": "executed",
            }
            records.append(record)
            if index == 0:
                repeated = _execute_actions(environment, snapshot, actions, horizons)
                repeatability = {
                    "cache_key": prediction_record["cache_key"],
                    "exact": repeated == outcome,
                    "first": outcome,
                    "second": repeated,
                }
                if repeated != outcome:
                    raise RuntimeError(f"prediction execution is not repeatable: {spec.key}")
    finally:
        environment.close()
    return records, repeatability


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gpu-index", type=int, default=0, help="physical EGL GPU index")
    parser.add_argument("--matrix-dir", type=Path, default=DEFAULT_MATRIX_DIR)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument(
        "--task-key",
        action="append",
        default=[],
        help="manifest task key; repeat to select several (default: all matrix tasks)",
    )
    parser.add_argument(
        "--horizon",
        action="append",
        type=int,
        default=[],
        help="action prefix checkpoint; repeat to select several (default: 8,16,32)",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    if args.gpu_index < 0:
        raise ValueError("gpu-index must be non-negative")
    horizons = tuple(sorted(args.horizon or (8, 16, 32)))
    if any(horizon <= 0 or horizon > 32 for horizon in horizons):
        raise ValueError("execution horizons must be in [1, 32]")
    if len(horizons) != len(set(horizons)):
        raise ValueError("execution horizons must be unique")

    matrix_dir = args.matrix_dir.expanduser().resolve()
    manifest_path = args.manifest.expanduser().resolve()
    matrix_path = matrix_dir / "matrix-index.json"
    matrix = _load_matrix(matrix_path)
    manifest = load_libero_cf_manifest(manifest_path)
    matrix_task_keys = matrix.get("task_keys")
    if not isinstance(matrix_task_keys, list) or not all(
        isinstance(key, str) for key in matrix_task_keys
    ):
        raise ValueError("matrix task_keys are invalid")
    selected_keys = args.task_key or matrix_task_keys
    specs = manifest.select(selected_keys)
    cf._configure_process(args.gpu_index, matrix_dir / "executions")

    records: list[dict[str, object]] = []
    repeatability: list[dict[str, object]] = []
    failures: list[dict[str, object]] = []
    for spec in specs:
        try:
            task_records, task_repeatability = _run_task(
                matrix_dir,
                matrix,
                spec,
                horizons,
                libero_revision=manifest.libero_revision,
                benchmark_id=manifest.benchmark_id,
            )
            records.extend(task_records)
            repeatability.append({"task_key": spec.key, **task_repeatability})
        except Exception as error:
            failures.append(
                {
                    "task_key": spec.key,
                    "status": "failed",
                    "error_type": type(error).__name__,
                    "error": str(error),
                }
            )
        _write_json(
            matrix_dir / "execution-index.json",
            {
                "schema_version": "0.1",
                "benchmark_id": manifest.benchmark_id,
                "model_id": matrix.get("model_id"),
                "source_matrix_sha256": _sha256_file(matrix_path),
                "manifest_sha256": _sha256_file(manifest_path),
                "horizons": list(horizons),
                "expected_executions": sum(len(_task_records(matrix, task.key)) for task in specs),
                "completed_executions": len(records),
                "failed_tasks": failures,
                "repeatability": repeatability,
                "records": records,
            },
        )
    if failures:
        raise RuntimeError(
            f"{len(failures)}/{len(specs)} prediction-execution tasks failed; "
            f"inspect {matrix_dir / 'execution-index.json'}"
        )
    print(f"wrote execution index: {matrix_dir / 'execution-index.json'}")


if __name__ == "__main__":
    main()
