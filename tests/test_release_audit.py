import hashlib
import io
import json
import tarfile
import zipfile
from pathlib import Path

import pytest

from wamprobe import __version__
from wamprobe.cli import main
from wamprobe.release_audit import audit_release


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_release_fixture(root: Path) -> tuple[Path, Path]:
    dist = root / "dist"
    dist.mkdir()
    wheel = dist / f"wamprobe-{__version__}-py3-none-any.whl"
    dist_info = f"wamprobe-{__version__}.dist-info"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr("wamprobe/__init__.py", f'__version__ = "{__version__}"\n')
        archive.writestr(
            f"{dist_info}/METADATA",
            "Metadata-Version: 2.4\n"
            "Name: wamprobe\n"
            f"Version: {__version__}\n"
            "License-Expression: Apache-2.0\n",
        )
        archive.writestr(
            f"{dist_info}/entry_points.txt",
            "[console_scripts]\nwamprobe = wamprobe.cli:main\n",
        )

    sdist = dist / f"wamprobe-{__version__}.tar.gz"
    prefix = f"wamprobe-{__version__}"
    with tarfile.open(sdist, "w:gz") as archive:
        for name, payload in (
            ("LICENSE", b"Apache-2.0\n"),
            ("README.md", b"# WAMProbe\n"),
            ("pyproject.toml", f'[project]\nversion = "{__version__}"\n'.encode()),
        ):
            info = tarfile.TarInfo(f"{prefix}/{name}")
            info.size = len(payload)
            archive.addfile(info, io.BytesIO(payload))

    evidence = root / "evidence.json"
    evidence.write_text('{"result": "verified"}\n', encoding="utf-8")
    manifest = root / "evidence-manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "schema_version": "0.1",
                "release_version": __version__,
                "committed_evidence": [
                    {
                        "path": "evidence.json",
                        "kind": "test-evidence",
                        "sha256": _sha256(evidence),
                    }
                ],
                "external_evidence": [],
            }
        ),
        encoding="utf-8",
    )
    return dist, manifest


def test_release_audit_verifies_archives_and_committed_evidence(tmp_path: Path) -> None:
    dist, manifest = _write_release_fixture(tmp_path)
    output = tmp_path / "release-audit.json"

    audit = audit_release(
        dist_dir=dist,
        evidence_manifest=manifest,
        repository_root=tmp_path,
        source_commit="a" * 40,
        source_date_epoch=1_700_000_000,
        output_path=output,
    )

    assert audit.release_version == __version__
    assert {artifact.kind for artifact in audit.artifacts} == {"wheel", "sdist"}
    assert audit.committed_evidence[0].path == "evidence.json"
    assert json.loads(output.read_text(encoding="utf-8"))["source_commit"] == "a" * 40


def test_release_audit_rejects_tampered_evidence(tmp_path: Path) -> None:
    dist, manifest = _write_release_fixture(tmp_path)
    (tmp_path / "evidence.json").write_text("tampered\n", encoding="utf-8")

    with pytest.raises(ValueError, match="checksum"):
        audit_release(
            dist_dir=dist,
            evidence_manifest=manifest,
            repository_root=tmp_path,
            source_commit="b" * 40,
            source_date_epoch=1_700_000_000,
        )


def test_release_audit_cli_writes_manifest(tmp_path: Path) -> None:
    dist, manifest = _write_release_fixture(tmp_path)
    output = tmp_path / "release-audit.json"

    assert (
        main(
            [
                "release-audit",
                "--dist",
                str(dist),
                "--evidence-manifest",
                str(manifest),
                "--repository-root",
                str(tmp_path),
                "--source-commit",
                "c" * 40,
                "--source-date-epoch",
                "1700000000",
                "--output",
                str(output),
            ]
        )
        == 0
    )
    assert output.is_file()
