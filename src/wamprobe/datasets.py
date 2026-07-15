"""Versioned JSONL interchange for paired intervention suites."""

from __future__ import annotations

import hashlib
import json
import math
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from wamprobe.api.manipulation import (
    ManipulationAction,
    ManipulationContext,
    ManipulationInterventionGroup,
    ManipulationInterventionSuite,
    ManipulationState,
)
from wamprobe.api.types import (
    Action2D,
    Context2D,
    InterventionGroup,
    InterventionSuite,
    Vec2,
)

SCHEMA_VERSION = "0.1"
InterventionDataset = InterventionSuite | ManipulationInterventionSuite


class DatasetValidationError(ValueError):
    """Raised when an intervention dataset violates its schema or checksum."""


@dataclass(frozen=True, slots=True)
class DatasetSummary:
    """Identity and size of a serialized intervention dataset."""

    schema_version: str
    benchmark_id: str
    records: int
    sha256: str


def _canonical_json(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _sha256(value: object) -> str:
    return hashlib.sha256(_canonical_json(value)).hexdigest()


def _vec_payload(vector: Vec2) -> list[float]:
    return [vector.x, vector.y]


def _pointmass_record(group: InterventionGroup, benchmark_id: str) -> dict[str, object]:
    return {
        "schema_version": SCHEMA_VERSION,
        "benchmark_id": benchmark_id,
        "state_kind": "pointmass-2d",
        "context": {
            "context_id": group.context.context_id,
            "position": _vec_payload(group.context.position),
            "goal": _vec_payload(group.context.goal),
        },
        "actions": [
            {"name": action.name, "delta": _vec_payload(action.delta)} for action in group.actions
        ],
    }


def _manipulation_record(
    group: ManipulationInterventionGroup,
    benchmark_id: str,
) -> dict[str, object]:
    state = group.context.initial_state
    return {
        "schema_version": SCHEMA_VERSION,
        "benchmark_id": benchmark_id,
        "state_kind": "manipulation-2d",
        "context": {
            "context_id": group.context.context_id,
            "initial_state": {
                "effector_position": _vec_payload(state.effector_position),
                "object_position": _vec_payload(state.object_position),
                "gripper_closed": state.gripper_closed,
                "object_attached": state.object_attached,
                "in_contact": state.in_contact,
            },
            "goal": _vec_payload(group.context.goal),
        },
        "actions": [
            {
                "name": action.name,
                "effector_delta": _vec_payload(action.effector_delta),
                "close_gripper": action.close_gripper,
            }
            for action in group.actions
        ],
    }


def _records(suite: InterventionDataset) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    if isinstance(suite, InterventionSuite):
        base_records = [_pointmass_record(group, suite.benchmark_id) for group in suite.groups]
    elif isinstance(suite, ManipulationInterventionSuite):
        base_records = [_manipulation_record(group, suite.benchmark_id) for group in suite.groups]
    else:
        raise TypeError("unsupported intervention suite type")
    for base in base_records:
        record = dict(base)
        record["record_sha256"] = _sha256(base)
        records.append(record)
    return records


def _dataset_bytes(suite: InterventionDataset) -> bytes:
    return b"".join(_canonical_json(record) + b"\n" for record in _records(suite))


def intervention_dataset_sha256(suite: InterventionDataset) -> str:
    """Return the content identity of a suite's canonical JSONL representation."""

    return hashlib.sha256(_dataset_bytes(suite)).hexdigest()


def _atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary_path = Path(handle.name)
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        temporary_path.replace(path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def write_intervention_dataset(
    suite: InterventionDataset,
    path: Path,
) -> DatasetSummary:
    """Atomically write a deterministic, checksummed JSONL intervention suite."""

    payload = _dataset_bytes(suite)
    _atomic_write(path, payload)
    return DatasetSummary(
        schema_version=SCHEMA_VERSION,
        benchmark_id=suite.benchmark_id,
        records=len(suite.groups),
        sha256=hashlib.sha256(payload).hexdigest(),
    )


def _mapping(value: object, field: str) -> dict[str, object]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise DatasetValidationError(f"{field} must be an object")
    return cast(dict[str, object], value)


def _list(value: object, field: str) -> list[object]:
    if not isinstance(value, list):
        raise DatasetValidationError(f"{field} must be an array")
    return cast(list[object], value)


def _string(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DatasetValidationError(f"{field} must be a non-empty string")
    return value


def _boolean(value: object, field: str) -> bool:
    if not isinstance(value, bool):
        raise DatasetValidationError(f"{field} must be a boolean")
    return value


def _number(value: object, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise DatasetValidationError(f"{field} must be a finite number")
    result = float(value)
    if not math.isfinite(result):
        raise DatasetValidationError(f"{field} must be a finite number")
    return result


def _vec(value: object, field: str) -> Vec2:
    coordinates = _list(value, field)
    if len(coordinates) != 2:
        raise DatasetValidationError(f"{field} must contain exactly two coordinates")
    return Vec2(
        _number(coordinates[0], f"{field}[0]"),
        _number(coordinates[1], f"{field}[1]"),
    )


def _verify_record(record: dict[str, object], line_number: int) -> dict[str, object]:
    checksum = _string(record.get("record_sha256"), f"line {line_number} record_sha256")
    base = {key: value for key, value in record.items() if key != "record_sha256"}
    if checksum != _sha256(base):
        raise DatasetValidationError(f"line {line_number} record_sha256 mismatch")
    if record.get("schema_version") != SCHEMA_VERSION:
        raise DatasetValidationError(f"line {line_number} uses unsupported schema_version")
    return base


def _parse_pointmass(
    record: dict[str, object],
    line_number: int,
) -> InterventionGroup:
    context_payload = _mapping(record.get("context"), f"line {line_number} context")
    context = Context2D(
        _string(context_payload.get("context_id"), "context.context_id"),
        _vec(context_payload.get("position"), "context.position"),
        _vec(context_payload.get("goal"), "context.goal"),
    )
    actions: list[Action2D] = []
    for index, raw_action in enumerate(_list(record.get("actions"), "actions")):
        action = _mapping(raw_action, f"actions[{index}]")
        actions.append(
            Action2D(
                _string(action.get("name"), f"actions[{index}].name"),
                _vec(action.get("delta"), f"actions[{index}].delta"),
            )
        )
    try:
        return InterventionGroup(context, tuple(actions))
    except ValueError as error:
        raise DatasetValidationError(str(error)) from error


def _parse_manipulation(
    record: dict[str, object],
    line_number: int,
) -> ManipulationInterventionGroup:
    context_payload = _mapping(record.get("context"), f"line {line_number} context")
    state_payload = _mapping(context_payload.get("initial_state"), "context.initial_state")
    try:
        state = ManipulationState(
            effector_position=_vec(
                state_payload.get("effector_position"),
                "context.initial_state.effector_position",
            ),
            object_position=_vec(
                state_payload.get("object_position"),
                "context.initial_state.object_position",
            ),
            gripper_closed=_boolean(
                state_payload.get("gripper_closed"),
                "context.initial_state.gripper_closed",
            ),
            object_attached=_boolean(
                state_payload.get("object_attached"),
                "context.initial_state.object_attached",
            ),
            in_contact=_boolean(
                state_payload.get("in_contact"),
                "context.initial_state.in_contact",
            ),
        )
        context = ManipulationContext(
            _string(context_payload.get("context_id"), "context.context_id"),
            state,
            _vec(context_payload.get("goal"), "context.goal"),
        )
        actions: list[ManipulationAction] = []
        for index, raw_action in enumerate(_list(record.get("actions"), "actions")):
            action = _mapping(raw_action, f"actions[{index}]")
            actions.append(
                ManipulationAction(
                    _string(action.get("name"), f"actions[{index}].name"),
                    _vec(
                        action.get("effector_delta"),
                        f"actions[{index}].effector_delta",
                    ),
                    _boolean(
                        action.get("close_gripper"),
                        f"actions[{index}].close_gripper",
                    ),
                )
            )
        return ManipulationInterventionGroup(context, tuple(actions))
    except ValueError as error:
        raise DatasetValidationError(str(error)) from error


def load_intervention_dataset(path: Path) -> InterventionDataset:
    """Load a checksummed JSONL suite and restore its typed representation."""

    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as error:
        raise DatasetValidationError(f"could not read dataset: {error}") from error
    if not lines:
        raise DatasetValidationError("intervention dataset must not be empty")

    benchmark_id: str | None = None
    state_kind: str | None = None
    pointmass_groups: list[InterventionGroup] = []
    manipulation_groups: list[ManipulationInterventionGroup] = []
    context_ids: set[str] = set()
    for line_number, line in enumerate(lines, start=1):
        try:
            raw: object = json.loads(line)
        except json.JSONDecodeError as error:
            raise DatasetValidationError(f"line {line_number} is not valid JSON") from error
        record = _verify_record(_mapping(raw, f"line {line_number}"), line_number)
        record_benchmark = _string(record.get("benchmark_id"), "benchmark_id")
        record_kind = _string(record.get("state_kind"), "state_kind")
        if benchmark_id is None:
            benchmark_id = record_benchmark
            state_kind = record_kind
        elif record_benchmark != benchmark_id or record_kind != state_kind:
            raise DatasetValidationError("all records must share benchmark_id and state_kind")

        if record_kind == "pointmass-2d":
            pointmass_group = _parse_pointmass(record, line_number)
            pointmass_groups.append(pointmass_group)
            context_id = pointmass_group.context.context_id
        elif record_kind == "manipulation-2d":
            manipulation_group = _parse_manipulation(record, line_number)
            manipulation_groups.append(manipulation_group)
            context_id = manipulation_group.context.context_id
        else:
            raise DatasetValidationError(f"unsupported state_kind: {record_kind}")
        if context_id in context_ids:
            raise DatasetValidationError(f"duplicate context_id: {context_id}")
        context_ids.add(context_id)

    if benchmark_id is None or state_kind is None:
        raise DatasetValidationError("intervention dataset must not be empty")
    if state_kind == "pointmass-2d":
        return InterventionSuite(benchmark_id, tuple(pointmass_groups))
    return ManipulationInterventionSuite(benchmark_id, tuple(manipulation_groups))
