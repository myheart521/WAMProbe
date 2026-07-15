# Changelog

All notable changes to WAMProbe will be documented here.

## [Unreleased]

### Added

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
