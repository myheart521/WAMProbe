#!/usr/bin/env python3
"""Build, reproduce, audit, and smoke-test a WAMProbe release candidate."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path
from typing import cast


def _run(
    command: list[str],
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        env=env,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )


def _git(root: Path, *arguments: str) -> str:
    return _run(["git", *arguments], cwd=root).stdout.strip()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _artifact_hashes(directory: Path) -> dict[str, str]:
    artifacts = sorted((*directory.glob("*.whl"), *directory.glob("*.tar.gz")))
    if len(artifacts) != 2:
        raise RuntimeError("candidate build must produce exactly one wheel and one sdist")
    return {artifact.name: _sha256(artifact) for artifact in artifacts}


def _project_version(root: Path) -> str:
    payload = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    project = payload.get("project")
    if not isinstance(project, dict) or not isinstance(project.get("version"), str):
        raise RuntimeError("pyproject.toml has no project version")
    return cast(str, project["version"])


def _build(uv: str, root: Path, output: Path, env: dict[str, str]) -> None:
    _run(
        [
            uv,
            "build",
            "--clear",
            "--no-create-gitignore",
            "--out-dir",
            str(output),
        ],
        cwd=root,
        env=env,
    )


def _clean_install_smoke(root: Path, wheel: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="wamprobe-install-") as raw_directory:
        directory = Path(raw_directory)
        environment = directory / "venv"
        _run([sys.executable, "-m", "venv", str(environment)], cwd=directory)
        binary_dir = environment / ("Scripts" if os.name == "nt" else "bin")
        python = binary_dir / ("python.exe" if os.name == "nt" else "python")
        wamprobe = binary_dir / ("wamprobe.exe" if os.name == "nt" else "wamprobe")
        _run(
            [str(python), "-m", "pip", "install", "--no-deps", "--no-index", str(wheel)],
            cwd=directory,
        )
        clean_env = os.environ.copy()
        clean_env.pop("PYTHONPATH", None)
        _run([str(wamprobe), "--help"], cwd=directory, env=clean_env)
        output = directory / "smoke-run"
        _run(
            [
                str(wamprobe),
                "demo",
                "--contexts",
                "2",
                "--seed",
                "7",
                "--output",
                str(output),
            ],
            cwd=directory,
            env=clean_env,
        )
        if not (output / "summary.json").is_file():
            raise RuntimeError("clean wheel smoke did not create summary.json")
        installed_version = _run(
            [str(python), "-c", "import wamprobe; print(wamprobe.__version__)"],
            cwd=directory,
            env=clean_env,
        ).stdout.strip()
        if installed_version != _project_version(root):
            raise RuntimeError("clean wheel version does not match pyproject.toml")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dist-dir",
        type=Path,
        default=Path("dist/release-candidate"),
    )
    parser.add_argument(
        "--evidence-manifest",
        type=Path,
        default=Path("release/evidence-manifest-v0.1.json"),
    )
    parser.add_argument("--allow-dirty", action="store_true")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    dist_dir = (root / args.dist_dir).resolve()
    evidence_manifest = (root / args.evidence_manifest).resolve()
    if not dist_dir.is_relative_to(root / "dist"):
        raise RuntimeError("release candidate output must stay below repository dist/")
    if _git(root, "status", "--porcelain", "--untracked-files=all") and not args.allow_dirty:
        raise RuntimeError("release candidate requires a clean Git worktree")

    uv = shutil.which("uv")
    if uv is None:
        raise RuntimeError("uv is required to build the release candidate")
    source_commit = _git(root, "rev-parse", "HEAD")
    source_date_epoch = int(_git(root, "show", "-s", "--format=%ct", "HEAD"))
    env = os.environ.copy()
    env["SOURCE_DATE_EPOCH"] = str(source_date_epoch)

    _build(uv, root, dist_dir, env)
    first_hashes = _artifact_hashes(dist_dir)
    with tempfile.TemporaryDirectory(prefix="wamprobe-rebuild-") as raw_rebuild:
        rebuild = Path(raw_rebuild)
        _build(uv, root, rebuild, env)
        second_hashes = _artifact_hashes(rebuild)
    if first_hashes != second_hashes:
        raise RuntimeError("release artifacts are not reproducible with SOURCE_DATE_EPOCH")

    manifest = dist_dir / "release-manifest.json"
    _run(
        [
            sys.executable,
            "-m",
            "wamprobe",
            "release-audit",
            "--dist",
            str(dist_dir),
            "--evidence-manifest",
            str(evidence_manifest),
            "--repository-root",
            str(root),
            "--source-commit",
            source_commit,
            "--source-date-epoch",
            str(source_date_epoch),
            "--output",
            str(manifest),
        ],
        cwd=root,
        env=env,
    )
    wheel = next(dist_dir.glob("*.whl"))
    _clean_install_smoke(root, wheel)

    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["checks"].extend(
        ["double-build-sha256-reproducibility", "clean-wheel-install-and-demo"]
    )
    payload["reproducible_build"] = {
        "source_date_epoch": source_date_epoch,
        "matched": True,
        "artifact_sha256": first_hashes,
    }
    payload["clean_install_smoke"] = {
        "network_disabled_for_install": True,
        "dependencies": "none",
        "commands": ["wamprobe --help", "wamprobe demo --contexts 2 --seed 7"],
        "passed": True,
    }
    manifest.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"WAMProbe {_project_version(root)} release candidate verified")
    print(f"Source commit: {source_commit}")
    print(f"Manifest: {manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
