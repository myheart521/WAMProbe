"""Content-addressed, corruption-detecting prediction cache."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import cast


class CacheCorruptionError(RuntimeError):
    """Raised when a cache entry no longer matches its content identity."""


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


@dataclass(frozen=True, slots=True)
class PredictionCacheRequest:
    """All inputs that can change a cached prediction payload."""

    namespace: str
    model_id: str
    benchmark_id: str
    context_id: str
    action_name: str
    horizon: int
    seed: int
    input_sha256: str
    configuration_sha256: str

    def __post_init__(self) -> None:
        text_fields = (
            self.namespace,
            self.model_id,
            self.benchmark_id,
            self.context_id,
            self.action_name,
        )
        if any(not value.strip() for value in text_fields):
            raise ValueError("cache request text fields must not be empty")
        if self.horizon <= 0:
            raise ValueError("cache request horizon must be positive")
        for field_name, checksum in (
            ("input_sha256", self.input_sha256),
            ("configuration_sha256", self.configuration_sha256),
        ):
            if len(checksum) != 64 or any(
                character not in "0123456789abcdef" for character in checksum
            ):
                raise ValueError(f"{field_name} must be a lowercase SHA256 digest")

    @property
    def cache_key(self) -> str:
        """Return a stable key over every request field."""

        return _sha256(asdict(self))

    @classmethod
    def from_object(cls, value: object) -> PredictionCacheRequest:
        """Restore and validate a request stored inside a cache entry."""

        if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
            raise CacheCorruptionError("request must be an object")
        payload = cast(dict[str, object], value)
        expected = {
            "namespace",
            "model_id",
            "benchmark_id",
            "context_id",
            "action_name",
            "horizon",
            "seed",
            "input_sha256",
            "configuration_sha256",
        }
        if payload.keys() != expected:
            raise CacheCorruptionError("request fields do not match the cache schema")
        string_fields = (
            "namespace",
            "model_id",
            "benchmark_id",
            "context_id",
            "action_name",
            "input_sha256",
            "configuration_sha256",
        )
        if any(not isinstance(payload[field], str) for field in string_fields):
            raise CacheCorruptionError("request string field has an invalid type")
        horizon = payload["horizon"]
        seed = payload["seed"]
        if isinstance(horizon, bool) or not isinstance(horizon, int):
            raise CacheCorruptionError("request horizon has an invalid type")
        if isinstance(seed, bool) or not isinstance(seed, int):
            raise CacheCorruptionError("request seed has an invalid type")
        try:
            return cls(
                namespace=cast(str, payload["namespace"]),
                model_id=cast(str, payload["model_id"]),
                benchmark_id=cast(str, payload["benchmark_id"]),
                context_id=cast(str, payload["context_id"]),
                action_name=cast(str, payload["action_name"]),
                horizon=horizon,
                seed=seed,
                input_sha256=cast(str, payload["input_sha256"]),
                configuration_sha256=cast(str, payload["configuration_sha256"]),
            )
        except ValueError as error:
            raise CacheCorruptionError(str(error)) from error


@dataclass(frozen=True, slots=True)
class CacheAudit:
    """Integrity summary over all entries beneath a cache root."""

    entries: int
    corrupt_entries: int

    @property
    def passed(self) -> bool:
        """Whether every discovered entry passed integrity checks."""

        return self.corrupt_entries == 0


class PredictionCache:
    """Atomic JSON cache that never silently replaces corrupt entries."""

    schema_version = "0.1"

    def __init__(self, root: Path) -> None:
        self.root = root

    def path_for(self, request: PredictionCacheRequest) -> Path:
        """Return the sharded path for a request."""

        key = request.cache_key
        return self.root / key[:2] / f"{key}.json"

    @staticmethod
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

    @staticmethod
    def _mapping(value: object, field: str) -> dict[str, object]:
        if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
            raise CacheCorruptionError(f"{field} must be an object")
        return cast(dict[str, object], value)

    def _load_path(
        self,
        path: Path,
        expected_request: PredictionCacheRequest | None = None,
    ) -> dict[str, object]:
        try:
            raw: object = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise CacheCorruptionError(f"cache entry is unreadable: {path}") from error
        entry = self._mapping(raw, "cache entry")
        if entry.get("schema_version") != self.schema_version:
            raise CacheCorruptionError("cache schema_version mismatch")
        request = PredictionCacheRequest.from_object(entry.get("request"))
        cache_key = entry.get("cache_key")
        if not isinstance(cache_key, str) or cache_key != request.cache_key:
            raise CacheCorruptionError("cache_key mismatch")
        if path.stem != cache_key:
            raise CacheCorruptionError("cache filename does not match cache_key")
        if expected_request is not None and request != expected_request:
            raise CacheCorruptionError("cache request mismatch")
        payload = self._mapping(entry.get("payload"), "payload")
        payload_sha256 = entry.get("payload_sha256")
        if not isinstance(payload_sha256, str) or payload_sha256 != _sha256(payload):
            raise CacheCorruptionError("payload_sha256 mismatch")
        return payload

    def load(self, request: PredictionCacheRequest) -> dict[str, object] | None:
        """Return a verified payload, or ``None`` when no entry exists."""

        path = self.path_for(request)
        if not path.exists():
            return None
        return self._load_path(path, request)

    def store(
        self,
        request: PredictionCacheRequest,
        payload: dict[str, object],
    ) -> Path:
        """Atomically persist a JSON-compatible payload under its request key."""

        path = self.path_for(request)
        if path.exists():
            existing = self._load_path(path, request)
            if existing != payload:
                raise CacheCorruptionError("valid cache entry already contains another payload")
            return path
        entry: dict[str, object] = {
            "schema_version": self.schema_version,
            "cache_key": request.cache_key,
            "request": asdict(request),
            "payload": payload,
            "payload_sha256": _sha256(payload),
        }
        self._atomic_write(path, _canonical_json(entry) + b"\n")
        return path

    def resolve(
        self,
        request: PredictionCacheRequest,
        producer: Callable[[], dict[str, object]],
    ) -> tuple[dict[str, object], bool]:
        """Load an entry or produce it once and store it for later resumption."""

        cached = self.load(request)
        if cached is not None:
            return cached, True
        payload = producer()
        self.store(request, payload)
        return payload, False

    def audit(self) -> CacheAudit:
        """Validate every JSON entry beneath the cache root."""

        paths = sorted(self.root.glob("*/*.json")) if self.root.exists() else []
        corrupt_entries = 0
        for path in paths:
            try:
                self._load_path(path)
            except CacheCorruptionError:
                corrupt_entries += 1
        return CacheAudit(entries=len(paths), corrupt_entries=corrupt_entries)
