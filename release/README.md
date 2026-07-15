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

```text
wamprobe-<version>-py3-none-any.whl
wamprobe-<version>.tar.gz
release-manifest.json
```

The GitHub `Release candidate` workflow repeats this process and adds GitHub build
provenance attestations. It is manual-dispatch only.

## Public release boundary

Before publishing, a maintainer must review the candidate manifest, confirm the version
and changelog, obtain one independent clean-environment smoke report, configure the PyPI
Trusted Publisher for the repository/environment, and approve both the Git tag and GitHub
Release text. Public `v0.1.0` publication is intentionally not automated from this Draft PR.

The guarded `Publish to PyPI` workflow is manual-dispatch only, runs only when the selected
ref is a tag, requires the typed confirmation to equal that tag, verifies that
`v<pyproject-version>` equals the tag, rebuilds the clean candidate, and uses short-lived
GitHub OIDC through the protected `pypi` environment. It contains no API token and does not
create a GitHub Release. Repository administrators must configure the PyPI Trusted
Publisher and require environment approval before the first dispatch.

Rollback for a bad pre-release means yanking the affected PyPI file (without deleting its
audit record), marking the GitHub Release as a pre-release with a warning, and preparing a
new version. Published filenames and tags are immutable and must never be overwritten.
