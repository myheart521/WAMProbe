# Release candidate procedure

WAMProbe separates candidate verification from public release. The candidate workflow
builds and attests artifacts but cannot publish to PyPI or create a GitHub Release.

## Local candidate

Run from a clean commit with the locked development environment:

```bash
uv sync --extra dev --locked
.venv/bin/python scripts/build_release_candidate.py
```

The script fixes `SOURCE_DATE_EPOCH` to the source commit timestamp, builds the wheel and
sdist twice, requires byte-identical SHA256 values, validates archive paths and package
metadata, checks every committed evidence hash, installs the wheel without network or
dependencies in a fresh virtual environment, and runs the CLI/demo smoke. Outputs remain
below ignored `dist/release-candidate/`:

The sdist uses an explicit source/package-metadata allowlist instead of Hatch's default VCS
file discovery, so a normal clone, shallow Actions checkout, and Git worktree select the
same content.

```text
wamprobe-<version>-py3-none-any.whl
wamprobe-<version>.tar.gz
release-manifest.json
```

The GitHub `Release candidate` workflow repeats this process and adds GitHub build
provenance attestations. It is manual-dispatch only.

## Public release boundary

The audited `v0.1.0rc1` artifacts are available from the
[GitHub pre-release](https://github.com/myheart521/WAMProbe/releases/tag/v0.1.0rc1), and
the wheel and sdist have GitHub build-provenance attestations. The independent clean-smoke
request is tracked in [Issue #2](https://github.com/myheart521/WAMProbe/issues/2). PyPI
publication is pending the one-time Trusted Publisher registration for this new project.

Before publishing, a maintainer must review the candidate manifest, confirm the version
and changelog, obtain one independent clean-environment smoke report, configure the PyPI
Trusted Publisher for the repository/environment, and approve both the Git tag and GitHub
Release text. Final `v0.1.0` publication remains a separate maintainer decision after the
release-candidate review.

The guarded `Publish to PyPI` workflow is manual-dispatch only, runs only when the selected
ref is a tag, requires the typed confirmation to equal that tag, verifies that
`v<pyproject-version>` equals the tag, rebuilds the clean candidate, and uses short-lived
GitHub OIDC through the protected `pypi` environment. It contains no API token and does not
create a GitHub Release. Repository administrators must configure the PyPI Trusted
Publisher and require environment approval before the first dispatch.

Rollback for a bad pre-release means yanking the affected PyPI file (without deleting its
audit record), marking the GitHub Release as a pre-release with a warning, and preparing a
new version. Published filenames and tags are immutable and must never be overwritten.
