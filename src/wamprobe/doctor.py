"""Validate pinned local model artifacts without importing model frameworks."""

from __future__ import annotations

import hashlib
import json
import string
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import cast


class ModelManifestError(ValueError):
    """Raised when a model manifest is malformed or unsafe."""


@dataclass(frozen=True, slots=True)
class FileRequirement:
    """One file that must be present under a model repository snapshot."""

    path: str
    expected_bytes: int | None = None
    sha256: str | None = None


@dataclass(frozen=True, slots=True)
class ModelRequirement:
    """Pinned model repository and the files WAMProbe needs from it."""

    name: str
    provider: str
    repository: str
    revision: str
    license: str
    target: str
    download_mode: str
    expected_bytes: int
    files: tuple[FileRequirement, ...]


@dataclass(frozen=True, slots=True)
class ModelManifest:
    """Required model artifacts for one WAMProbe development milestone."""

    schema_version: str
    store_root: str
    required_models: tuple[ModelRequirement, ...]


@dataclass(frozen=True, slots=True)
class FileCheck:
    """Validation result for one required local artifact."""

    path: str
    exists: bool
    size_ok: bool | None
    sha256_ok: bool | None
    detail: str

    @property
    def passed(self) -> bool:
        """Return whether the file satisfies every requested check."""

        return (
            self.exists
            and self.size_ok is not False
            and self.sha256_ok is not False
            and self.detail != "Git LFS pointer; payload not downloaded"
        )

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-compatible representation."""

        return {
            "path": self.path,
            "exists": self.exists,
            "size_ok": self.size_ok,
            "sha256_ok": self.sha256_ok,
            "detail": self.detail,
            "passed": self.passed,
        }


@dataclass(frozen=True, slots=True)
class ModelCheck:
    """Validation result for one pinned model repository."""

    name: str
    target: str
    revision: str
    revision_ok: bool | None
    expected_bytes: int
    files: tuple[FileCheck, ...]

    @property
    def passed(self) -> bool:
        """Return whether the repository satisfies all required checks."""

        return self.revision_ok is not False and all(item.passed for item in self.files)

    @property
    def missing_paths(self) -> tuple[str, ...]:
        """Return required paths that are not regular files."""

        return tuple(item.path for item in self.files if not item.exists)

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-compatible representation."""

        return {
            "name": self.name,
            "target": self.target,
            "revision": self.revision,
            "revision_ok": self.revision_ok,
            "expected_bytes": self.expected_bytes,
            "passed": self.passed,
            "files": [item.to_dict() for item in self.files],
        }


@dataclass(frozen=True, slots=True)
class DoctorReport:
    """Complete local model-store validation report."""

    schema_version: str
    store_root: Path
    hashes_verified: bool
    models: tuple[ModelCheck, ...]

    @property
    def passed(self) -> bool:
        """Return whether every required model passed."""

        return all(model.passed for model in self.models)

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-compatible representation."""

        return {
            "schema_version": self.schema_version,
            "store_root": str(self.store_root),
            "hashes_verified": self.hashes_verified,
            "passed": self.passed,
            "models": [model.to_dict() for model in self.models],
        }


def _as_mapping(value: object, location: str) -> dict[str, object]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise ModelManifestError(f"{location} must be a JSON object")
    return cast(dict[str, object], value)


def _as_list(value: object, location: str) -> list[object]:
    if not isinstance(value, list):
        raise ModelManifestError(f"{location} must be a JSON array")
    return cast(list[object], value)


def _as_string(value: object, location: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ModelManifestError(f"{location} must be a non-empty string")
    return value


def _as_positive_int(value: object, location: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ModelManifestError(f"{location} must be a positive integer")
    return value


def _safe_relative_path(value: object, location: str) -> str:
    path_text = _as_string(value, location)
    posix_path = PurePosixPath(path_text)
    windows_path = PureWindowsPath(path_text)
    if (
        posix_path.is_absolute()
        or windows_path.is_absolute()
        or windows_path.drive
        or ".." in posix_path.parts
        or "\\" in path_text
    ):
        raise ModelManifestError(f"{location} must be a safe relative path")
    return posix_path.as_posix()


def _hex_digest(value: object, length: int, location: str) -> str:
    digest = _as_string(value, location).lower()
    if len(digest) != length or any(character not in string.hexdigits for character in digest):
        raise ModelManifestError(f"{location} must be a {length}-character hexadecimal digest")
    return digest


def _parse_file(value: object, location: str) -> FileRequirement:
    data = _as_mapping(value, location)
    return FileRequirement(
        path=_safe_relative_path(data.get("path"), f"{location}.path"),
        expected_bytes=_as_positive_int(data.get("bytes"), f"{location}.bytes"),
        sha256=_hex_digest(data.get("sha256"), 64, f"{location}.sha256"),
    )


def _parse_model(value: object, index: int) -> ModelRequirement:
    location = f"required_now[{index}]"
    data = _as_mapping(value, location)
    mode = _as_string(data.get("download_mode"), f"{location}.download_mode")
    if mode == "full_snapshot":
        paths = _as_list(data.get("required_paths"), f"{location}.required_paths")
        files = tuple(
            FileRequirement(path=_safe_relative_path(path, f"{location}.required_paths[{i}]"))
            for i, path in enumerate(paths)
        )
    elif mode == "selected_files":
        raw_files = _as_list(data.get("required_files"), f"{location}.required_files")
        files = tuple(
            _parse_file(item, f"{location}.required_files[{i}]") for i, item in enumerate(raw_files)
        )
    else:
        raise ModelManifestError(
            f"{location}.download_mode must be 'full_snapshot' or 'selected_files'"
        )
    if not files:
        raise ModelManifestError(f"{location} must declare at least one required file")
    file_paths = [item.path for item in files]
    if len(file_paths) != len(set(file_paths)):
        raise ModelManifestError(f"{location} contains duplicate required file paths")
    return ModelRequirement(
        name=_as_string(data.get("name"), f"{location}.name"),
        provider=_as_string(data.get("provider"), f"{location}.provider"),
        repository=_as_string(data.get("repository"), f"{location}.repository"),
        revision=_hex_digest(data.get("revision"), 40, f"{location}.revision"),
        license=_as_string(data.get("license"), f"{location}.license"),
        target=_safe_relative_path(data.get("target"), f"{location}.target"),
        download_mode=mode,
        expected_bytes=_as_positive_int(data.get("expected_bytes"), f"{location}.expected_bytes"),
        files=files,
    )


def load_manifest(path: Path) -> ModelManifest:
    """Load and validate a pinned upstream-model manifest."""

    try:
        raw = cast(object, json.loads(path.read_text(encoding="utf-8")))
    except json.JSONDecodeError as error:
        raise ModelManifestError(f"invalid JSON in model manifest: {path}") from error
    data = _as_mapping(raw, "manifest")
    version = _as_string(data.get("schema_version"), "schema_version")
    if version != "0.1":
        raise ModelManifestError(f"unsupported model manifest schema: {version}")
    raw_models = _as_list(data.get("required_now"), "required_now")
    if not raw_models:
        raise ModelManifestError("required_now must contain at least one model")
    models = tuple(_parse_model(value, index) for index, value in enumerate(raw_models))
    targets = [model.target for model in models]
    if len(targets) != len(set(targets)):
        raise ModelManifestError("required_now contains duplicate target directories")
    return ModelManifest(
        schema_version=version,
        store_root=_safe_relative_path(data.get("store_root"), "store_root"),
        required_models=models,
    )


def _local_path(root: Path, relative_path: str) -> Path:
    return root.joinpath(*PurePosixPath(relative_path).parts)


def _is_lfs_pointer(path: Path) -> bool:
    if path.stat().st_size > 512:
        return False
    try:
        first_line = path.read_text(encoding="utf-8").splitlines()[0]
    except (UnicodeDecodeError, IndexError):
        return False
    return first_line == "version https://git-lfs.github.com/spec/v1"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(8 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _git_head(repository_root: Path) -> str | None:
    head_path = repository_root / ".git" / "HEAD"
    try:
        head = head_path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return None
    if not head.startswith("ref: "):
        return head
    reference = repository_root / ".git" / head.removeprefix("ref: ")
    try:
        return reference.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return None


def _huggingface_revisions(
    repository_root: Path,
    requirements: tuple[FileRequirement, ...],
) -> set[str]:
    revisions: set[str] = set()
    metadata_root = repository_root / ".cache" / "huggingface" / "download"
    for requirement in requirements:
        metadata = _local_path(metadata_root, f"{requirement.path}.metadata")
        try:
            with metadata.open(encoding="utf-8") as stream:
                revision = stream.readline(256).strip()
        except FileNotFoundError:
            continue
        if revision:
            revisions.add(revision)
    return revisions


def _check_file(
    model_root: Path,
    requirement: FileRequirement,
    *,
    verify_hashes: bool,
) -> FileCheck:
    path = _local_path(model_root, requirement.path)
    if not path.is_file():
        return FileCheck(
            path=requirement.path,
            exists=False,
            size_ok=None,
            sha256_ok=None,
            detail="missing required file",
        )
    if _is_lfs_pointer(path):
        return FileCheck(
            path=requirement.path,
            exists=True,
            size_ok=False if requirement.expected_bytes is not None else None,
            sha256_ok=None,
            detail="Git LFS pointer; payload not downloaded",
        )
    size_ok = (
        None
        if requirement.expected_bytes is None
        else path.stat().st_size == requirement.expected_bytes
    )
    sha256_ok = (
        _sha256(path) == requirement.sha256
        if verify_hashes and requirement.sha256 is not None
        else None
    )
    details: list[str] = []
    if size_ok is False:
        details.append(
            f"size mismatch: expected {requirement.expected_bytes}, got {path.stat().st_size}"
        )
    if sha256_ok is False:
        details.append("SHA256 mismatch")
    if not details:
        details.append("present")
    return FileCheck(
        path=requirement.path,
        exists=True,
        size_ok=size_ok,
        sha256_ok=sha256_ok,
        detail="; ".join(details),
    )


def check_model_store(
    manifest: ModelManifest,
    *,
    store_root: Path | None = None,
    verify_hashes: bool = False,
) -> DoctorReport:
    """Check required local artifacts without loading model code or pickle data."""

    root = store_root if store_root is not None else Path(manifest.store_root)
    model_checks: list[ModelCheck] = []
    for model in manifest.required_models:
        model_root = _local_path(root, model.target)
        git_head = _git_head(model_root)
        huggingface_revisions = _huggingface_revisions(model_root, model.files)
        if git_head is not None:
            revision_ok = git_head == model.revision
        elif huggingface_revisions:
            revision_ok = huggingface_revisions == {model.revision}
        else:
            revision_ok = None
        files = tuple(
            _check_file(model_root, requirement, verify_hashes=verify_hashes)
            for requirement in model.files
        )
        model_checks.append(
            ModelCheck(
                name=model.name,
                target=model.target,
                revision=model.revision,
                revision_ok=revision_ok,
                expected_bytes=model.expected_bytes,
                files=files,
            )
        )
    return DoctorReport(
        schema_version=manifest.schema_version,
        store_root=root,
        hashes_verified=verify_hashes,
        models=tuple(model_checks),
    )
