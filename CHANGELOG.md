# Changelog

All notable changes to WAMProbe will be documented here.

## [0.1.0rc1] - 2026-07-15

This candidate is published as a
[GitHub pre-release](https://github.com/myheart521/WAMProbe/releases/tag/v0.1.0rc1) for
reproducibility review. It is not yet published to PyPI or as a final GitHub Release.

### Added

- Strict MkDocs documentation, GitHub Pages deployment, repository-local Markdown link
  validation, and Draft 2020-12 validation of canonical public-schema instances.
- Typed alpha `WAMAdapter` protocol and capability declaration.
- Analytic PointMass-2D paired counterfactual benchmark.
- Oracle, copy-last-frame, wrong-direction, and action-agnostic reference baselines.
- Action Dependence, Counterfactual Direction Accuracy, No-op Stability, state ADE,
  and Top-1 Regret metrics.
- JSON/Markdown reports, schemas, CLI, CI, and contributor documentation.
- Phase 0 evidence map covering 15 reported WAM/VLA failure modes.
- Version-pinned audit selecting StarWAM as the first real adapter target.
- Provider-scoped local model store with pinned revisions, expected paths, sizes, and
  checksums for the first StarWAM integration.
- `wamprobe doctor` with safe manifest parsing, revision/size/hash validation, and JSON
  output for local model artifacts.
- Reproducible StarWAM environment preflight and a narrow patch that restricts verified
  inference checkpoint loads to PyTorch's weights-only deserializer.
- Checksummed intervention JSONL, corruption-detecting content-addressed prediction cache,
  exact-context comparison, and report-only regeneration commands.
- Contact-aware BlockPush-2D and attachment-aware Gripper-Catch analytic benchmarks.
- Four-family LIBERO-CF-Mini generation with exact snapshot restore, repeat, branch-order,
  provenance, and cache validation.
- A pinned StarWAM 36-prediction matrix and 36 action-chunk simulator executions with
  explicit unsupported-metric skips and retained zero-success results.
- Dependency-free PSNR/global-SSIM diagnostics and a traditional-video/control-value
  counterexample study.
- Minimal score-execute-observe closed-loop replanning with context-block intervals and
  offline-ranking/return association analysis.
- Release artifact audit, candidate workflow, clean-wheel smoke test, evidence manifest,
  and technical-report draft.

### Changed

- GitHub workflows now use the current Node 24-compatible major releases of official
  checkout, Python setup, artifact, Pages, provenance, and uv setup actions.
