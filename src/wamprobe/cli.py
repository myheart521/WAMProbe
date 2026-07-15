"""Command-line entry point for the CPU-first WAMProbe MVP."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from wamprobe.adapters.baselines import (
    ActionAgnosticAdapter,
    CopyLastFrameAdapter,
    NoisyLinearAdapter,
    OraclePointMassAdapter,
    WrongDirectionAdapter,
)
from wamprobe.api.model import WAMAdapter
from wamprobe.benchmarks.pointmass import PointMass2D
from wamprobe.doctor import ModelManifestError, check_model_store, load_manifest
from wamprobe.evaluation import evaluate
from wamprobe.reporting import write_reports


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="wamprobe",
        description="Counterfactual evaluation for World Action Models",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    demo = subparsers.add_parser("demo", help="run the PointMass-2D baseline comparison")
    demo.add_argument("--contexts", type=int, default=12, help="number of shared contexts")
    demo.add_argument("--seed", type=int, default=7, help="deterministic suite seed")
    demo.add_argument("--horizon", type=int, default=4, help="prediction horizon")
    demo.add_argument(
        "--output",
        type=Path,
        default=Path("runs/pointmass-demo"),
        help="directory for summary.json, report.md, and report.html",
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
    return parser


def _run_demo(args: argparse.Namespace) -> int:
    benchmark = PointMass2D(horizon=args.horizon)
    suite = benchmark.make_suite(contexts=args.contexts, seed=args.seed)
    adapters: list[WAMAdapter] = [
        OraclePointMassAdapter(benchmark),
        NoisyLinearAdapter(),
        CopyLastFrameAdapter(),
        WrongDirectionAdapter(benchmark),
        ActionAgnosticAdapter(),
    ]
    results = [evaluate(adapter, benchmark, suite, seed=args.seed) for adapter in adapters]
    summary_path, report_path, html_path = write_reports(
        args.output,
        benchmark=benchmark.benchmark_id,
        results=results,
        seed=args.seed,
    )
    print("WAMProbe demo complete")
    print(f"JSON: {summary_path}")
    print(f"Markdown: {report_path}")
    print(f"HTML: {html_path}")
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
    parser.error(f"unsupported command: {args.command}")
    return 2
