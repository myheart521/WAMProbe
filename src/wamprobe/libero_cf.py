"""Pinned, dependency-free manifest contract for LIBERO-CF-Mini."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import cast


def _sha256_digest(value: object, field: str) -> str:
    if not isinstance(value, str) or len(value) != 64:
        raise ValueError(f"{field} must be a lowercase SHA256 digest")
    if any(character not in "0123456789abcdef" for character in value):
        raise ValueError(f"{field} must be a lowercase SHA256 digest")
    return value


def _git_revision(value: object, field: str) -> str:
    if not isinstance(value, str) or len(value) != 40:
        raise ValueError(f"{field} must be a lowercase Git commit")
    if any(character not in "0123456789abcdef" for character in value):
        raise ValueError(f"{field} must be a lowercase Git commit")
    return value


def _string(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value


def _integer(value: object, field: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"{field} must be an integer >= {minimum}")
    return value


def _mapping(value: object, field: str) -> dict[str, object]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise ValueError(f"{field} must be an object")
    return cast(dict[str, object], value)


@dataclass(frozen=True, slots=True)
class LiberoTaskSpec:
    """One immutable simulator origin selected for the mini benchmark."""

    key: str
    task_family: str
    task_suite: str
    task_id: int
    task: str
    init_state_index: int
    wait_steps: int
    seed: int
    bddl_sha256: str
    init_states_sha256: str
    init_states_shape: tuple[int, int]
    init_states_dtype: str
    problem_folder: str
    bddl_file: str
    init_states_file: str

    def __post_init__(self) -> None:
        for field_name in (
            "key",
            "task_family",
            "task_suite",
            "task",
            "init_states_dtype",
            "problem_folder",
            "bddl_file",
            "init_states_file",
        ):
            _string(getattr(self, field_name), field_name)
        _integer(self.task_id, "task_id")
        _integer(self.init_state_index, "init_state_index")
        _integer(self.wait_steps, "wait_steps")
        _integer(self.seed, "seed")
        _sha256_digest(self.bddl_sha256, "bddl_sha256")
        _sha256_digest(self.init_states_sha256, "init_states_sha256")
        if len(self.init_states_shape) != 2 or any(
            dimension <= 0 for dimension in self.init_states_shape
        ):
            raise ValueError("init_states_shape must contain two positive dimensions")
        if self.init_state_index >= self.init_states_shape[0]:
            raise ValueError("init_state_index is outside init_states_shape")

    @property
    def context_id(self) -> str:
        """Return the stable shared-context identifier used by artifacts and caches."""

        suite = self.task_suite.replace("_", "-")
        return (
            f"{suite}-task{self.task_id}-init{self.init_state_index}"
            f"-wait{self.wait_steps}-seed{self.seed}"
        )

    @classmethod
    def from_object(cls, value: object, index: int) -> LiberoTaskSpec:
        """Strictly restore one task from a manifest record."""

        payload = _mapping(value, f"tasks[{index}]")
        expected = {
            "key",
            "task_family",
            "task_suite",
            "task_id",
            "task",
            "init_state_index",
            "wait_steps",
            "seed",
            "bddl_sha256",
            "init_states_sha256",
            "init_states_shape",
            "init_states_dtype",
            "problem_folder",
            "bddl_file",
            "init_states_file",
        }
        if payload.keys() != expected:
            raise ValueError(f"tasks[{index}] fields do not match schema 0.1")
        shape = payload["init_states_shape"]
        if not isinstance(shape, list) or len(shape) != 2:
            raise ValueError("init_states_shape must be a two-element array")
        return cls(
            key=_string(payload["key"], "key"),
            task_family=_string(payload["task_family"], "task_family"),
            task_suite=_string(payload["task_suite"], "task_suite"),
            task_id=_integer(payload["task_id"], "task_id"),
            task=_string(payload["task"], "task"),
            init_state_index=_integer(payload["init_state_index"], "init_state_index"),
            wait_steps=_integer(payload["wait_steps"], "wait_steps"),
            seed=_integer(payload["seed"], "seed"),
            bddl_sha256=_sha256_digest(payload["bddl_sha256"], "bddl_sha256"),
            init_states_sha256=_sha256_digest(
                payload["init_states_sha256"],
                "init_states_sha256",
            ),
            init_states_shape=(
                _integer(shape[0], "init_states_shape[0]", minimum=1),
                _integer(shape[1], "init_states_shape[1]", minimum=1),
            ),
            init_states_dtype=_string(payload["init_states_dtype"], "init_states_dtype"),
            problem_folder=_string(payload["problem_folder"], "problem_folder"),
            bddl_file=_string(payload["bddl_file"], "bddl_file"),
            init_states_file=_string(payload["init_states_file"], "init_states_file"),
        )


@dataclass(frozen=True, slots=True)
class LiberoCFManifest:
    """Versioned benchmark selection and upstream provenance."""

    benchmark_id: str
    libero_revision: str
    upstream_license: str
    tasks: tuple[LiberoTaskSpec, ...]
    schema_version: str = "0.1"

    def __post_init__(self) -> None:
        if self.schema_version != "0.1":
            raise ValueError("unsupported LIBERO-CF manifest schema_version")
        _string(self.benchmark_id, "benchmark_id")
        _git_revision(self.libero_revision, "libero_revision")
        _string(self.upstream_license, "upstream_license")
        if not 3 <= len(self.tasks) <= 5:
            raise ValueError("LIBERO-CF-Mini requires three to five task families")
        keys = [task.key for task in self.tasks]
        families = [task.task_family for task in self.tasks]
        context_ids = [task.context_id for task in self.tasks]
        if len(keys) != len(set(keys)):
            raise ValueError("LIBERO-CF task keys must be unique")
        if len(families) != len(set(families)):
            raise ValueError("LIBERO-CF task families must be unique")
        if len(context_ids) != len(set(context_ids)):
            raise ValueError("LIBERO-CF context IDs must be unique")

    def select(self, keys: list[str] | None = None) -> tuple[LiberoTaskSpec, ...]:
        """Select manifest-order tasks, rejecting unknown or duplicate keys."""

        if not keys:
            return self.tasks
        if len(keys) != len(set(keys)):
            raise ValueError("selected LIBERO-CF task keys must be unique")
        requested = set(keys)
        selected = tuple(task for task in self.tasks if task.key in requested)
        missing = requested - {task.key for task in selected}
        if missing:
            raise ValueError(f"unknown LIBERO-CF task keys: {sorted(missing)}")
        return selected


def load_libero_cf_manifest(path: Path) -> LiberoCFManifest:
    """Load and strictly validate the pinned LIBERO-CF-Mini manifest."""

    try:
        raw: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError(f"could not read LIBERO-CF manifest: {error}") from error
    payload = _mapping(raw, "manifest")
    expected = {
        "schema_version",
        "benchmark_id",
        "libero_revision",
        "upstream_license",
        "tasks",
    }
    if payload.keys() != expected:
        raise ValueError("LIBERO-CF manifest fields do not match schema 0.1")
    raw_tasks = payload["tasks"]
    if not isinstance(raw_tasks, list):
        raise ValueError("tasks must be an array")
    return LiberoCFManifest(
        schema_version=_string(payload["schema_version"], "schema_version"),
        benchmark_id=_string(payload["benchmark_id"], "benchmark_id"),
        libero_revision=_git_revision(payload["libero_revision"], "libero_revision"),
        upstream_license=_string(payload["upstream_license"], "upstream_license"),
        tasks=tuple(
            LiberoTaskSpec.from_object(task, index) for index, task in enumerate(raw_tasks)
        ),
    )
