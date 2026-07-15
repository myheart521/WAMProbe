"""Command-line entry point for the CPU-first WAMProbe MVP."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections.abc import Sequence
from dataclasses import asdict
from pathlib import Path
from typing import cast

from wamprobe.adapters.baselines import (
    ActionAgnosticAdapter,
    CopyLastFrameAdapter,
    NoisyLinearAdapter,
    OraclePointMassAdapter,
    WrongDirectionAdapter,
)
from wamprobe.adapters.manipulation import (
    ActionAgnosticManipulationAdapter,
    CopyLastManipulationAdapter,
    NoisyManipulationAdapter,
    OracleManipulationAdapter,
    WrongDirectionManipulationAdapter,
)
from wamprobe.api.manipulation import (
    ManipulationAdapter,
    ManipulationBenchmark,
    ManipulationInterventionSuite,
)
from wamprobe.api.model import WAMAdapter
from wamprobe.api.types import InterventionSuite
from wamprobe.benchmarks.blockpush import BlockPush2D
from wamprobe.benchmarks.gripper_catch import GripperCatch
from wamprobe.benchmarks.pointmass import PointMass2D
from wamprobe.cache import PredictionCache, PredictionCacheRequest
from wamprobe.datasets import (
    DatasetValidationError,
    intervention_dataset_sha256,
    load_intervention_dataset,
    write_intervention_dataset,
)
from wamprobe.doctor import ModelManifestError, check_model_store, load_manifest
from wamprobe.evaluation import EvaluationResult, evaluate
from wamprobe.experiments import analyze_action_experiment, write_action_experiment_report
from wamprobe.manipulation_evaluation import evaluate_manipulation
from wamprobe.reporting import write_reports
from wamprobe.stats import paired_metric_comparison


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="wamprobe",
        description="Counterfactual evaluation for World Action Models",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    demo = subparsers.add_parser("demo", help="run an analytic baseline comparison")
    demo.add_argument(
        "--benchmark",
        choices=("pointmass", "blockpush", "gripper-catch"),
        default="pointmass",
        help="analytic benchmark to evaluate",
    )
    demo.add_argument("--contexts", type=int, default=12, help="number of shared contexts")
    demo.add_argument("--seed", type=int, default=7, help="deterministic suite seed")
    demo.add_argument("--horizon", type=int, default=4, help="prediction horizon")
    demo.add_argument(
        "--output",
        type=Path,
        default=Path("runs/pointmass-demo"),
        help="directory for JSON, JSONL, Markdown, and HTML reports",
    )
    demo.add_argument(
        "--cache-dir",
        type=Path,
        default=None,
        help="optional content-addressed cache for resumable model results",
    )
    doctor = subparsers.add_parser("doctor", help="validate pinned local model artifacts")
    doctor.add_argument(
        "--manifest",
        type=Path,
        default=Path("configs/models/upstream_models.json"),
        help="pinned upstream model manifest",
    )
    doctor.add_argument(
        "--store-root",
        type=Path,
        default=None,
        help="override the manifest's local model-store root",
    )
    doctor.add_argument(
        "--verify-hashes",
        action="store_true",
        help="stream SHA256 verification for files that declare a checksum",
    )
    doctor.add_argument("--json", action="store_true", help="emit a machine-readable report")

    report = subparsers.add_parser("report", help="rebuild reports from a summary.json")
    report.add_argument("summary", type=Path, help="summary.json file or containing run directory")
    report.add_argument("--output", type=Path, required=True, help="report output directory")
    report.add_argument("--resamples", type=int, default=1000, help="bootstrap resamples")
    report.add_argument("--seed", type=int, default=0, help="bootstrap seed")

    compare = subparsers.add_parser("compare", help="compare paired cached evaluation results")
    compare.add_argument("left", type=Path, help="left summary file or run directory")
    compare.add_argument("right", type=Path, help="right summary file or run directory")
    compare.add_argument("--left-model", required=True, help="model ID in the left summary")
    compare.add_argument("--right-model", required=True, help="model ID in the right summary")
    compare.add_argument("--metric", required=True, help="per-context metric to compare")
    compare.add_argument("--resamples", type=int, default=1000, help="bootstrap resamples")
    compare.add_argument("--seed", type=int, default=0, help="bootstrap seed")
    compare.add_argument("--output", type=Path, required=True, help="comparison JSON path")

    dataset_export = subparsers.add_parser(
        "dataset-export",
        help="export a deterministic built-in intervention suite",
    )
    dataset_export.add_argument(
        "--benchmark",
        choices=("pointmass", "blockpush", "gripper-catch"),
        required=True,
    )
    dataset_export.add_argument("--contexts", type=int, default=12)
    dataset_export.add_argument("--seed", type=int, default=7)
    dataset_export.add_argument("--output", type=Path, required=True)

    dataset_validate = subparsers.add_parser(
        "dataset-validate",
        help="validate checksums and schema for an intervention JSONL file",
    )
    dataset_validate.add_argument("dataset", type=Path)

    experiment_report = subparsers.add_parser(
        "experiment-report",
        help="analyze a cached real-model prediction/execution matrix",
    )
    experiment_report.add_argument("matrix", type=Path, help="matrix-index.json path")
    experiment_report.add_argument("execution", type=Path, help="execution-index.json path")
    experiment_report.add_argument("--output", type=Path, required=True)
    return parser


def _stable_sha256(value: object) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def _request_for(
    *,
    model_id: str,
    benchmark_id: str,
    suite_sha256: str,
    horizon: int,
    seed: int,
    configuration: object,
) -> PredictionCacheRequest:
    return PredictionCacheRequest(
        namespace="wamprobe-evaluation-v0.1",
        model_id=model_id,
        benchmark_id=benchmark_id,
        context_id=f"suite-{suite_sha256[:16]}",
        action_name="all",
        horizon=horizon,
        seed=seed,
        input_sha256=suite_sha256,
        configuration_sha256=_stable_sha256(configuration),
    )


def _pointmass_results(
    args: argparse.Namespace,
) -> tuple[str, list[EvaluationResult], int]:
    benchmark = PointMass2D(horizon=args.horizon)
    suite = benchmark.make_suite(contexts=args.contexts, seed=args.seed)
    adapters: list[WAMAdapter] = [
        OraclePointMassAdapter(benchmark),
        NoisyLinearAdapter(),
        CopyLastFrameAdapter(),
        WrongDirectionAdapter(benchmark),
        ActionAgnosticAdapter(),
    ]
    cache = PredictionCache(args.cache_dir) if args.cache_dir is not None else None
    suite_sha256 = intervention_dataset_sha256(suite)
    results: list[EvaluationResult] = []
    cache_hits = 0
    for adapter in adapters:
        if cache is None:
            results.append(evaluate(adapter, benchmark, suite, seed=args.seed))
            continue
        request = _request_for(
            model_id=adapter.capabilities.model_id,
            benchmark_id=benchmark.benchmark_id,
            suite_sha256=suite_sha256,
            horizon=benchmark.horizon,
            seed=args.seed,
            configuration={
                "capabilities": adapter.capabilities.to_dict(),
                "benchmark": {
                    "horizon": benchmark.horizon,
                    "action_scale": benchmark.action_scale,
                },
            },
        )

        def produce(current_adapter: WAMAdapter = adapter) -> dict[str, object]:
            return cast(
                dict[str, object],
                evaluate(current_adapter, benchmark, suite, seed=args.seed).to_dict(),
            )

        payload, hit = cache.resolve(request, produce)
        if hit:
            cache_hits += 1
            adapter.close()
        results.append(EvaluationResult.from_dict(payload))
    return benchmark.benchmark_id, results, cache_hits


def _manipulation_results(
    args: argparse.Namespace,
) -> tuple[str, list[EvaluationResult], int]:
    benchmark: ManipulationBenchmark
    if args.benchmark == "blockpush":
        benchmark = BlockPush2D(horizon=args.horizon)
    else:
        benchmark = GripperCatch(horizon=args.horizon)
    suite = benchmark.make_suite(contexts=args.contexts, seed=args.seed)
    adapters: list[ManipulationAdapter] = [
        OracleManipulationAdapter(benchmark),
        NoisyManipulationAdapter(benchmark),
        CopyLastManipulationAdapter(),
        WrongDirectionManipulationAdapter(benchmark),
        ActionAgnosticManipulationAdapter(benchmark),
    ]
    cache = PredictionCache(args.cache_dir) if args.cache_dir is not None else None
    suite_sha256 = intervention_dataset_sha256(suite)
    results: list[EvaluationResult] = []
    cache_hits = 0
    for adapter in adapters:
        if cache is None:
            results.append(evaluate_manipulation(adapter, benchmark, suite, seed=args.seed))
            continue
        request = _request_for(
            model_id=adapter.capabilities.model_id,
            benchmark_id=benchmark.benchmark_id,
            suite_sha256=suite_sha256,
            horizon=benchmark.horizon,
            seed=args.seed,
            configuration={
                "capabilities": adapter.capabilities.to_dict(),
                "benchmark_type": type(benchmark).__name__,
                "horizon": benchmark.horizon,
            },
        )

        def produce(
            current_adapter: ManipulationAdapter = adapter,
        ) -> dict[str, object]:
            return cast(
                dict[str, object],
                evaluate_manipulation(
                    current_adapter,
                    benchmark,
                    suite,
                    seed=args.seed,
                ).to_dict(),
            )

        payload, hit = cache.resolve(request, produce)
        if hit:
            cache_hits += 1
            adapter.close()
        results.append(EvaluationResult.from_dict(payload))
    return benchmark.benchmark_id, results, cache_hits


def _run_demo(args: argparse.Namespace) -> int:
    benchmark_id, results, cache_hits = (
        _pointmass_results(args) if args.benchmark == "pointmass" else _manipulation_results(args)
    )
    summary_path, report_path, html_path = write_reports(
        args.output,
        benchmark=benchmark_id,
        results=results,
        seed=args.seed,
    )
    print("WAMProbe demo complete")
    print(f"JSON: {summary_path}")
    print(f"Markdown: {report_path}")
    print(f"HTML: {html_path}")
    if args.cache_dir is not None:
        print(f"Cache hits: {cache_hits}/{len(results)}")
    return 0


def _load_summary(source: Path) -> tuple[str, list[EvaluationResult]]:
    path = source / "summary.json" if source.is_dir() else source
    try:
        raw: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError(f"could not read summary: {error}") from error
    if not isinstance(raw, dict) or not all(isinstance(key, str) for key in raw):
        raise ValueError("summary must be a JSON object")
    payload = cast(dict[str, object], raw)
    if payload.get("schema_version") != "0.1":
        raise ValueError("summary uses an unsupported schema_version")
    benchmark = payload.get("benchmark")
    raw_results = payload.get("results")
    if not isinstance(benchmark, str) or not benchmark.strip():
        raise ValueError("summary benchmark must be a non-empty string")
    if not isinstance(raw_results, list) or not raw_results:
        raise ValueError("summary results must be a non-empty array")
    results = [EvaluationResult.from_dict(result) for result in raw_results]
    if any(result.benchmark != benchmark for result in results):
        raise ValueError("summary contains results for a different benchmark")
    return benchmark, results


def _run_report(args: argparse.Namespace) -> int:
    try:
        benchmark, results = _load_summary(args.summary)
        summary, markdown, html = write_reports(
            args.output,
            benchmark=benchmark,
            results=results,
            resamples=args.resamples,
            seed=args.seed,
        )
    except (OSError, ValueError) as error:
        print(f"WAMProbe report error: {error}", file=sys.stderr)
        return 2
    print(f"JSON: {summary}")
    print(f"Markdown: {markdown}")
    print(f"HTML: {html}")
    return 0


def _select_model(results: list[EvaluationResult], model_id: str) -> EvaluationResult:
    matches = [result for result in results if result.model_id == model_id]
    if len(matches) != 1:
        raise ValueError(f"expected exactly one result for model: {model_id}")
    return matches[0]


def _run_compare(args: argparse.Namespace) -> int:
    try:
        _, left_results = _load_summary(args.left)
        _, right_results = _load_summary(args.right)
        comparison = paired_metric_comparison(
            _select_model(left_results, args.left_model),
            _select_model(right_results, args.right_model),
            metric=args.metric,
            resamples=args.resamples,
            seed=args.seed,
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(asdict(comparison), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    except (OSError, ValueError) as error:
        print(f"WAMProbe compare error: {error}", file=sys.stderr)
        return 2
    print(f"Comparison: {args.output}")
    return 0


def _run_dataset_export(args: argparse.Namespace) -> int:
    suite: InterventionSuite | ManipulationInterventionSuite
    if args.benchmark == "pointmass":
        suite = PointMass2D().make_suite(contexts=args.contexts, seed=args.seed)
    elif args.benchmark == "blockpush":
        suite = BlockPush2D().make_suite(contexts=args.contexts, seed=args.seed)
    else:
        suite = GripperCatch().make_suite(contexts=args.contexts, seed=args.seed)
    try:
        summary = write_intervention_dataset(suite, args.output)
    except (OSError, TypeError, ValueError) as error:
        print(f"WAMProbe dataset export error: {error}", file=sys.stderr)
        return 2
    print(
        f"Exported {summary.records} intervention groups for "
        f"{summary.benchmark_id} ({summary.sha256})"
    )
    return 0


def _run_dataset_validate(args: argparse.Namespace) -> int:
    try:
        suite = load_intervention_dataset(args.dataset)
    except DatasetValidationError as error:
        print(f"WAMProbe dataset validation error: {error}", file=sys.stderr)
        return 2
    print(
        f"Validated {len(suite.groups)} intervention groups for {suite.benchmark_id} (schema 0.1)"
    )
    return 0


def _run_experiment_report(args: argparse.Namespace) -> int:
    try:
        analysis = analyze_action_experiment(args.matrix, args.execution)
        json_path, markdown_path = write_action_experiment_report(args.output, analysis)
    except (OSError, ValueError) as error:
        print(f"WAMProbe experiment report error: {error}", file=sys.stderr)
        return 2
    print(f"Experiment JSON: {json_path}")
    print(f"Experiment Markdown: {markdown_path}")
    return 0


def _run_doctor(args: argparse.Namespace) -> int:
    try:
        manifest = load_manifest(args.manifest)
        report = check_model_store(
            manifest,
            store_root=args.store_root,
            verify_hashes=args.verify_hashes,
        )
    except (OSError, ModelManifestError) as error:
        print(f"WAMProbe doctor error: {error}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    else:
        print("WAMProbe doctor")
        for model in report.models:
            status = "PASS" if model.passed else "FAIL"
            print(f"[{status}] {model.name} ({model.target})")
            for file_check in model.files:
                file_status = "PASS" if file_check.passed else "FAIL"
                print(f"  [{file_status}] {file_check.path}: {file_check.detail}")
            if model.revision_ok is False:
                print(f"  [FAIL] Local revision metadata does not match {model.revision}")
        passed_count = sum(model.passed for model in report.models)
        print(f"Summary: {passed_count}/{len(report.models)} required models passed")
        if not report.hashes_verified:
            print("SHA256: skipped (use --verify-hashes for full verification)")
    return 0 if report.passed else 1


def main(argv: Sequence[str] | None = None) -> int:
    """Run WAMProbe and return a process exit code."""

    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command == "demo":
        return _run_demo(args)
    if args.command == "doctor":
        return _run_doctor(args)
    if args.command == "report":
        return _run_report(args)
    if args.command == "compare":
        return _run_compare(args)
    if args.command == "dataset-export":
        return _run_dataset_export(args)
    if args.command == "dataset-validate":
        return _run_dataset_validate(args)
    if args.command == "experiment-report":
        return _run_experiment_report(args)
    parser.error(f"unsupported command: {args.command}")
    return 2
