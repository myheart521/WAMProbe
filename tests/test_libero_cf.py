import json
from pathlib import Path

import pytest

from wamprobe.libero_cf import load_libero_cf_manifest

MANIFEST = Path("configs/benchmarks/libero_cf_mini_v0.1.json")


def test_libero_cf_manifest_pins_four_distinct_task_families() -> None:
    manifest = load_libero_cf_manifest(MANIFEST)

    assert manifest.schema_version == "0.1"
    assert manifest.benchmark_id == "libero-cf-mini-v0.1"
    assert manifest.upstream_license == "MIT"
    assert len(manifest.tasks) == 4
    assert len({task.task_family for task in manifest.tasks}) == 4
    assert len({task.task_suite for task in manifest.tasks}) == 4
    assert all(len(task.bddl_sha256) == 64 for task in manifest.tasks)
    assert all(len(task.init_states_sha256) == 64 for task in manifest.tasks)
    assert all(task.context_id.endswith(f"seed{task.seed}") for task in manifest.tasks)


def test_libero_cf_manifest_selection_preserves_manifest_order() -> None:
    manifest = load_libero_cf_manifest(MANIFEST)

    selected = manifest.select(["goal-task0", "spatial-task0"])

    assert [task.key for task in selected] == ["spatial-task0", "goal-task0"]
    with pytest.raises(ValueError, match="unknown"):
        manifest.select(["not-a-task"])
    with pytest.raises(ValueError, match="unique"):
        manifest.select(["goal-task0", "goal-task0"])


def test_libero_cf_manifest_rejects_tampered_checksum(tmp_path: Path) -> None:
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    payload["tasks"][0]["bddl_sha256"] = "tampered"
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="bddl_sha256"):
        load_libero_cf_manifest(path)
