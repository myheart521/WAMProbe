"""Command-line entry point for the CPU-first WAMProbe MVP."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from wamprobe.adapters.baselines import (
    ActionAgnosticAdapter,
    CopyLastFrameAdapter,
    OraclePointMassAdapter,
    WrongDirectionAdapter,
)
from wamprobe.api.model import WAMAdapter
from wamprobe.benchmarks.pointmass import PointMass2D
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
        help="directory for summary.json and report.md",
    )
    return parser


def _run_demo(args: argparse.Namespace) -> int:
    benchmark = PointMass2D(horizon=args.horizon)
    suite = benchmark.make_suite(contexts=args.contexts, seed=args.seed)
    adapters: list[WAMAdapter] = [
        OraclePointMassAdapter(benchmark),
        CopyLastFrameAdapter(),
        WrongDirectionAdapter(benchmark),
        ActionAgnosticAdapter(),
    ]
    results = [evaluate(adapter, benchmark, suite, seed=args.seed) for adapter in adapters]
    summary_path, report_path = write_reports(
        args.output,
        benchmark=benchmark.benchmark_id,
        results=results,
    )
    print("WAMProbe demo complete")
    print(f"JSON: {summary_path}")
    print(f"Markdown: {report_path}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Run WAMProbe and return a process exit code."""

    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command == "demo":
        return _run_demo(args)
    parser.error(f"unsupported command: {args.command}")
    return 2
