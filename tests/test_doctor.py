import hashlib
import json
from pathlib import Path

import pytest

from wamprobe.cli import main
from wamprobe.doctor import ModelManifestError, check_model_store, load_manifest


def _write_manifest(path: Path, required_now: list[dict[str, object]]) -> Path:
    manifest = {
        "schema_version": "0.1",
        "store_root": "checkpoints/upstream",
        "required_now": required_now,
        "optional_later": [],
    }
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return path


def test_doctor_reports_missing_required_snapshot_file(tmp_path: Path) -> None:
    manifest_path = _write_manifest(
        tmp_path / "models.json",
        [
            {
                "name": "example-model",
                "provider": "huggingface",
                "repository": "owner/example-model",
                "revision": "a" * 40,
                "license": "Apache-2.0",
                "target": "huggingface/owner/example-model",
                "download_mode": "full_snapshot",
                "expected_bytes": 100,
                "required_paths": ["config.json", "weights/model.safetensors"],
            }
        ],
    )

    report = check_model_store(load_manifest(manifest_path), store_root=tmp_path / "models")

    assert not report.passed
    assert report.models[0].missing_paths == (
        "config.json",
        "weights/model.safetensors",
    )


def test_doctor_verifies_selected_file_size_and_hash(tmp_path: Path) -> None:
    store_root = tmp_path / "models"
    model_root = store_root / "modelscope" / "owner" / "model"
    model_root.mkdir(parents=True)
    payload = b"verified checkpoint bytes"
    checkpoint = model_root / "weights.bin"
    checkpoint.write_bytes(payload)
    digest = hashlib.sha256(payload).hexdigest()
    manifest_path = _write_manifest(
        tmp_path / "models.json",
        [
            {
                "name": "selected-model",
                "provider": "modelscope",
                "repository": "owner/model",
                "revision": "b" * 40,
                "license": "Apache-2.0",
                "target": "modelscope/owner/model",
                "download_mode": "selected_files",
                "expected_bytes": len(payload),
                "required_files": [
                    {
                        "path": "weights.bin",
                        "bytes": len(payload),
                        "sha256": digest,
                    }
                ],
            }
        ],
    )

    report = check_model_store(
        load_manifest(manifest_path),
        store_root=store_root,
        verify_hashes=True,
    )

    assert report.passed
    file_check = report.models[0].files[0]
    assert file_check.size_ok is True
    assert file_check.sha256_ok is True


def test_manifest_rejects_paths_that_escape_the_model_store(tmp_path: Path) -> None:
    manifest_path = _write_manifest(
        tmp_path / "models.json",
        [
            {
                "name": "unsafe-model",
                "provider": "huggingface",
                "repository": "owner/model",
                "revision": "c" * 40,
                "license": "Apache-2.0",
                "target": "../outside",
                "download_mode": "full_snapshot",
                "expected_bytes": 1,
                "required_paths": ["weights.bin"],
            }
        ],
    )

    with pytest.raises(ModelManifestError, match="safe relative path"):
        load_manifest(manifest_path)


def test_manifest_rejects_unsafe_required_file_path(tmp_path: Path) -> None:
    manifest_path = _write_manifest(
        tmp_path / "models.json",
        [
            {
                "name": "unsafe-file-model",
                "provider": "modelscope",
                "repository": "owner/model",
                "revision": "e" * 40,
                "license": "Apache-2.0",
                "target": "modelscope/owner/model",
                "download_mode": "selected_files",
                "expected_bytes": 1,
                "required_files": [
                    {
                        "path": "../../outside.bin",
                        "bytes": 1,
                        "sha256": "f" * 64,
                    }
                ],
            }
        ],
    )

    with pytest.raises(ModelManifestError, match="safe relative path"):
        load_manifest(manifest_path)


def test_doctor_rejects_lfs_pointer_and_wrong_git_revision(tmp_path: Path) -> None:
    store_root = tmp_path / "models"
    model_root = store_root / "modelscope" / "owner" / "model"
    (model_root / ".git").mkdir(parents=True)
    (model_root / ".git" / "HEAD").write_text("0" * 40, encoding="utf-8")
    pointer = model_root / "weights.bin"
    pointer.write_text(
        f"version https://git-lfs.github.com/spec/v1\noid sha256:{'1' * 64}\nsize 123\n",
        encoding="utf-8",
    )
    manifest_path = _write_manifest(
        tmp_path / "models.json",
        [
            {
                "name": "pointer-model",
                "provider": "modelscope",
                "repository": "owner/model",
                "revision": "1" * 40,
                "license": "Apache-2.0",
                "target": "modelscope/owner/model",
                "download_mode": "selected_files",
                "expected_bytes": 123,
                "required_files": [
                    {
                        "path": "weights.bin",
                        "bytes": 123,
                        "sha256": "1" * 64,
                    }
                ],
            }
        ],
    )

    report = check_model_store(load_manifest(manifest_path), store_root=store_root)

    assert not report.passed
    assert report.models[0].revision_ok is False
    assert report.models[0].files[0].detail == "Git LFS pointer; payload not downloaded"


def test_doctor_reports_checksum_mismatch(tmp_path: Path) -> None:
    store_root = tmp_path / "models"
    model_root = store_root / "modelscope" / "owner" / "model"
    model_root.mkdir(parents=True)
    payload = b"wrong"
    (model_root / "weights.bin").write_bytes(payload)
    manifest_path = _write_manifest(
        tmp_path / "models.json",
        [
            {
                "name": "bad-checksum-model",
                "provider": "modelscope",
                "repository": "owner/model",
                "revision": "2" * 40,
                "license": "Apache-2.0",
                "target": "modelscope/owner/model",
                "download_mode": "selected_files",
                "expected_bytes": len(payload),
                "required_files": [
                    {
                        "path": "weights.bin",
                        "bytes": len(payload),
                        "sha256": hashlib.sha256(b"right").hexdigest(),
                    }
                ],
            }
        ],
    )

    report = check_model_store(
        load_manifest(manifest_path),
        store_root=store_root,
        verify_hashes=True,
    )

    assert not report.passed
    assert report.models[0].files[0].size_ok is True
    assert report.models[0].files[0].sha256_ok is False
    assert report.models[0].files[0].detail == "SHA256 mismatch"


def test_doctor_checks_huggingface_download_revision(tmp_path: Path) -> None:
    store_root = tmp_path / "models"
    model_root = store_root / "huggingface" / "owner" / "model"
    metadata = model_root / ".cache" / "huggingface" / "download" / "config.json.metadata"
    metadata.parent.mkdir(parents=True)
    metadata.write_text(f"{'3' * 40}\netag\ntimestamp\n", encoding="utf-8")
    (model_root / "config.json").write_text("{}", encoding="utf-8")
    manifest_path = _write_manifest(
        tmp_path / "models.json",
        [
            {
                "name": "wrong-revision-model",
                "provider": "huggingface",
                "repository": "owner/model",
                "revision": "4" * 40,
                "license": "Apache-2.0",
                "target": "huggingface/owner/model",
                "download_mode": "full_snapshot",
                "expected_bytes": 2,
                "required_paths": ["config.json"],
            }
        ],
    )

    report = check_model_store(load_manifest(manifest_path), store_root=store_root)

    assert not report.passed
    assert report.models[0].revision_ok is False


def test_doctor_cli_reports_invalid_manifest(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    manifest_path = tmp_path / "models.json"
    manifest_path.write_text("not JSON", encoding="utf-8")

    exit_code = main(["doctor", "--manifest", str(manifest_path)])

    assert exit_code == 2
    assert "invalid JSON" in capsys.readouterr().err


def test_doctor_cli_emits_machine_readable_report(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    store_root = tmp_path / "models"
    model_root = store_root / "huggingface" / "owner" / "model"
    model_root.mkdir(parents=True)
    (model_root / "config.json").write_text("{}", encoding="utf-8")
    manifest_path = _write_manifest(
        tmp_path / "models.json",
        [
            {
                "name": "ready-model",
                "provider": "huggingface",
                "repository": "owner/model",
                "revision": "d" * 40,
                "license": "Apache-2.0",
                "target": "huggingface/owner/model",
                "download_mode": "full_snapshot",
                "expected_bytes": 2,
                "required_paths": ["config.json"],
            }
        ],
    )

    exit_code = main(
        [
            "doctor",
            "--manifest",
            str(manifest_path),
            "--store-root",
            str(store_root),
            "--json",
        ]
    )

    assert exit_code == 0
    output = json.loads(capsys.readouterr().out)
    assert output["passed"] is True
    assert output["models"][0]["name"] == "ready-model"
