import json
from pathlib import Path

import pytest

from wamprobe.api.manipulation import ManipulationInterventionSuite
from wamprobe.api.types import InterventionSuite
from wamprobe.benchmarks.blockpush import BlockPush2D
from wamprobe.benchmarks.gripper_catch import GripperCatch
from wamprobe.benchmarks.pointmass import PointMass2D
from wamprobe.cache import (
    CacheCorruptionError,
    PredictionCache,
    PredictionCacheRequest,
)
from wamprobe.datasets import (
    DatasetValidationError,
    load_intervention_dataset,
    write_intervention_dataset,
)


@pytest.mark.parametrize(
    "suite",
    [
        PointMass2D().make_suite(contexts=5, seed=7),
        BlockPush2D().make_suite(contexts=5, seed=7),
        GripperCatch().make_suite(contexts=5, seed=7),
    ],
)
def test_intervention_jsonl_round_trip_is_versioned_and_deterministic(
    tmp_path: Path,
    suite: InterventionSuite | ManipulationInterventionSuite,
) -> None:
    path = tmp_path / "interventions.jsonl"

    first = write_intervention_dataset(suite, path)
    first_bytes = path.read_bytes()
    second = write_intervention_dataset(suite, path)

    assert first == second
    assert first.records == 5
    assert first.schema_version == "0.1"
    assert len(first.sha256) == 64
    assert path.read_bytes() == first_bytes
    assert len(path.read_text(encoding="utf-8").splitlines()) == 5
    assert load_intervention_dataset(path) == suite


def test_intervention_jsonl_rejects_record_tampering(tmp_path: Path) -> None:
    path = tmp_path / "interventions.jsonl"
    write_intervention_dataset(PointMass2D().make_suite(contexts=2, seed=3), path)
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    records[0]["context"]["position"][0] += 0.5
    path.write_text(
        "\n".join(json.dumps(record, sort_keys=True) for record in records) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(DatasetValidationError, match="record_sha256"):
        load_intervention_dataset(path)


def _cache_request(*, model_id: str = "oracle") -> PredictionCacheRequest:
    return PredictionCacheRequest(
        namespace="unit-test-v0.1",
        model_id=model_id,
        benchmark_id="pointmass-2d-v0.1",
        context_id="suite-0001",
        action_name="all",
        horizon=4,
        seed=7,
        input_sha256="a" * 64,
        configuration_sha256="b" * 64,
    )


def test_prediction_cache_resumes_without_recomputing_valid_entries(tmp_path: Path) -> None:
    cache = PredictionCache(tmp_path / "cache")
    calls = 0

    def produce() -> dict[str, object]:
        nonlocal calls
        calls += 1
        return {"states": [[0.0, 1.0]], "complete": True}

    first, first_hit = cache.resolve(_cache_request(), produce)
    second, second_hit = cache.resolve(_cache_request(), produce)

    assert first == second
    assert not first_hit
    assert second_hit
    assert calls == 1
    assert cache.audit().passed
    assert cache.audit().entries == 1


def test_prediction_cache_detects_corruption_and_keys_configuration(tmp_path: Path) -> None:
    cache = PredictionCache(tmp_path / "cache")
    request = _cache_request()
    cache.store(request, {"value": 1.0})
    cache.store(_cache_request(model_id="copy-last"), {"value": 2.0})
    entry_path = cache.path_for(request)
    payload = json.loads(entry_path.read_text(encoding="utf-8"))
    payload["payload"]["value"] = 99.0
    entry_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(CacheCorruptionError, match="payload_sha256"):
        cache.load(request)
    audit = cache.audit()
    assert not audit.passed
    assert audit.entries == 2
    assert audit.corrupt_entries == 1
