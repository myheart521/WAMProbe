"""Release artifact and reproducibility-evidence auditing."""

from __future__ import annotations

import hashlib
import json
import re
import tarfile
import zipfile
from dataclasses import asdict, dataclass
from email.parser import Parser
from pathlib import Path, PurePosixPath
from typing import cast

from wamprobe import __version__

_COMMIT_PATTERN = re.compile(r"[0-9a-f]{40}")
_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
_FORBIDDEN_PARTS = {
    ".env",
    ".git",
    "checkpoints",
    "runs",
    "vendor",
}


@dataclass(frozen=True, slots=True)
class ReleaseArtifact:
    """One built distribution with its immutable identity."""

    name: str
    kind: str
    size_bytes: int
    sha256: str


@dataclass(frozen=True, slots=True)
class CommittedEvidence:
    """One repository evidence file verified against the release declaration."""

    path: str
    kind: str
    size_bytes: int
    sha256: str


@dataclass(frozen=True, slots=True)
class ReleaseAudit:
    """Machine-readable link from source commit to distributions and evidence."""

    release_version: str
    source_commit: str
    source_date_epoch: int
    artifacts: tuple[ReleaseArtifact, ...]
    evidence_manifest: str
    evidence_manifest_sha256: str
    committed_evidence: tuple[CommittedEvidence, ...]
    external_evidence: tuple[dict[str, object], ...]
    checks: tuple[str, ...]
    schema_version: str = "0.1"

    def to_dict(self) -> dict[str, object]:
        """Return a stable JSON-compatible audit record."""

        return {
            "schema_version": self.schema_version,
            "release_version": self.release_version,
            "source_commit": self.source_commit,
            "source_date_epoch": self.source_date_epoch,
            "artifacts": [asdict(artifact) for artifact in self.artifacts],
            "evidence_manifest": self.evidence_manifest,
            "evidence_manifest_sha256": self.evidence_manifest_sha256,
            "committed_evidence": [asdict(evidence) for evidence in self.committed_evidence],
            "external_evidence": list(self.external_evidence),
            "checks": list(self.checks),
        }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _json_object(path: Path) -> dict[str, object]:
    try:
        raw: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError(f"could not read release evidence manifest: {error}") from error
    if not isinstance(raw, dict) or not all(isinstance(key, str) for key in raw):
        raise ValueError("release evidence manifest must be a JSON object")
    return cast(dict[str, object], raw)


def _safe_archive_path(name: str) -> PurePosixPath:
    path = PurePosixPath(name)
    if path.is_absolute() or not path.parts or ".." in path.parts:
        raise ValueError(f"release archive contains an unsafe path: {name}")
    if any(part in _FORBIDDEN_PARTS for part in path.parts):
        raise ValueError(f"release archive contains a forbidden path: {name}")
    return path


def _verify_wheel(path: Path, version: str) -> None:
    try:
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
            archive_paths = [_safe_archive_path(name) for name in names]
            metadata_names = [name for name in names if name.endswith(".dist-info/METADATA")]
            entry_names = [name for name in names if name.endswith(".dist-info/entry_points.txt")]
            if len(metadata_names) != 1 or len(entry_names) != 1:
                raise ValueError("wheel must contain one METADATA and one entry_points.txt")
            if not any(path.parts[0] == "wamprobe" for path in archive_paths):
                raise ValueError("wheel does not contain the wamprobe package")
            metadata = Parser().parsestr(archive.read(metadata_names[0]).decode("utf-8"))
            if metadata.get("Name") != "wamprobe" or metadata.get("Version") != version:
                raise ValueError("wheel package name/version does not match the release")
            if metadata.get("License-Expression") != "Apache-2.0":
                raise ValueError("wheel does not declare the Apache-2.0 license expression")
            entry_points = archive.read(entry_names[0]).decode("utf-8")
            if "wamprobe = wamprobe.cli:main" not in entry_points:
                raise ValueError("wheel does not contain the wamprobe console entry point")
    except (OSError, UnicodeError, zipfile.BadZipFile) as error:
        raise ValueError(f"could not verify wheel: {error}") from error


def _verify_sdist(path: Path, version: str) -> None:
    required = {"LICENSE", "README.md", "pyproject.toml"}
    root = f"wamprobe-{version}"
    found: set[str] = set()
    try:
        with tarfile.open(path, "r:gz") as archive:
            for member in archive.getmembers():
                member_path = _safe_archive_path(member.name)
                if member.issym() or member.islnk():
                    raise ValueError("sdist must not contain symbolic or hard links")
                if member_path.parts[0] != root:
                    raise ValueError("sdist contains a path outside its versioned root")
                if len(member_path.parts) == 2:
                    found.add(member_path.parts[1])
    except (OSError, tarfile.TarError) as error:
        raise ValueError(f"could not verify sdist: {error}") from error
    missing = required - found
    if missing:
        raise ValueError(f"sdist is missing required files: {sorted(missing)}")


def _manifest_evidence(
    manifest: Path,
    *,
    repository_root: Path,
    version: str,
) -> tuple[tuple[CommittedEvidence, ...], tuple[dict[str, object], ...]]:
    payload = _json_object(manifest)
    if payload.get("schema_version") != "0.1":
        raise ValueError("release evidence manifest uses an unsupported schema_version")
    if payload.get("release_version") != version:
        raise ValueError("release evidence manifest version does not match the package")
    raw_committed = payload.get("committed_evidence")
    raw_external = payload.get("external_evidence")
    if not isinstance(raw_committed, list) or not raw_committed:
        raise ValueError("release evidence manifest needs committed_evidence")
    if not isinstance(raw_external, list):
        raise ValueError("release evidence manifest external_evidence must be an array")

    root = repository_root.resolve(strict=True)
    evidence: list[CommittedEvidence] = []
    seen_paths: set[str] = set()
    for item in raw_committed:
        if not isinstance(item, dict):
            raise ValueError("committed evidence entries must be JSON objects")
        path_value = item.get("path")
        kind = item.get("kind")
        expected_sha256 = item.get("sha256")
        if (
            not isinstance(path_value, str)
            or not path_value
            or not isinstance(kind, str)
            or not kind
            or not isinstance(expected_sha256, str)
            or _SHA256_PATTERN.fullmatch(expected_sha256) is None
        ):
            raise ValueError("committed evidence entry fields are invalid")
        relative = PurePosixPath(path_value)
        if relative.is_absolute() or ".." in relative.parts or path_value in seen_paths:
            raise ValueError("committed evidence paths must be unique safe relative paths")
        seen_paths.add(path_value)
        candidate = root.joinpath(*relative.parts)
        if candidate.is_symlink() or not candidate.is_file():
            raise ValueError(f"committed evidence is missing or unsafe: {path_value}")
        resolved = candidate.resolve(strict=True)
        if not resolved.is_relative_to(root):
            raise ValueError(f"committed evidence escapes the repository: {path_value}")
        actual_sha256 = _sha256(resolved)
        if actual_sha256 != expected_sha256:
            raise ValueError(f"committed evidence checksum mismatch: {path_value}")
        evidence.append(
            CommittedEvidence(
                path=path_value,
                kind=kind,
                size_bytes=resolved.stat().st_size,
                sha256=actual_sha256,
            )
        )

    external: list[dict[str, object]] = []
    for item in raw_external:
        if not isinstance(item, dict) or not all(isinstance(key, str) for key in item):
            raise ValueError("external evidence entries must be JSON objects")
        external.append(cast(dict[str, object], item))
    return tuple(evidence), tuple(external)


def audit_release(
    *,
    dist_dir: Path,
    evidence_manifest: Path,
    repository_root: Path,
    source_commit: str,
    source_date_epoch: int,
    output_path: Path | None = None,
    version: str = __version__,
) -> ReleaseAudit:
    """Verify distributions and evidence, then optionally write their traceability record."""

    if _COMMIT_PATTERN.fullmatch(source_commit) is None:
        raise ValueError("source_commit must be a lowercase 40-character Git SHA")
    if source_date_epoch <= 0:
        raise ValueError("source_date_epoch must be positive")
    if not dist_dir.is_dir():
        raise ValueError("release dist directory does not exist")

    wheels = sorted(dist_dir.glob("*.whl"))
    sdists = sorted(dist_dir.glob("*.tar.gz"))
    if len(wheels) != 1 or len(sdists) != 1:
        raise ValueError("release dist must contain exactly one wheel and one sdist")
    expected_wheel = f"wamprobe-{version}-py3-none-any.whl"
    expected_sdist = f"wamprobe-{version}.tar.gz"
    if wheels[0].name != expected_wheel or sdists[0].name != expected_sdist:
        raise ValueError("release artifact filenames do not match the package version")

    _verify_wheel(wheels[0], version)
    _verify_sdist(sdists[0], version)
    committed, external = _manifest_evidence(
        evidence_manifest,
        repository_root=repository_root,
        version=version,
    )
    artifacts = (
        ReleaseArtifact(
            name=wheels[0].name,
            kind="wheel",
            size_bytes=wheels[0].stat().st_size,
            sha256=_sha256(wheels[0]),
        ),
        ReleaseArtifact(
            name=sdists[0].name,
            kind="sdist",
            size_bytes=sdists[0].stat().st_size,
            sha256=_sha256(sdists[0]),
        ),
    )
    audit = ReleaseAudit(
        release_version=version,
        source_commit=source_commit,
        source_date_epoch=source_date_epoch,
        artifacts=artifacts,
        evidence_manifest=evidence_manifest.name,
        evidence_manifest_sha256=_sha256(evidence_manifest),
        committed_evidence=committed,
        external_evidence=external,
        checks=(
            "artifact-count-and-filenames",
            "archive-path-safety",
            "wheel-metadata-and-entry-point",
            "sdist-required-files",
            "committed-evidence-sha256",
        ),
    )
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(audit.to_dict(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    return audit
