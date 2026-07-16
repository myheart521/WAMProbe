"""Run the custom-adapter starter kit against PointMass2D."""

from __future__ import annotations

import argparse
from pathlib import Path

from examples.custom_adapter.adapter import LinearStateBackend, StarterWAMAdapter
from wamprobe.benchmarks.pointmass import PointMass2D
from wamprobe.evaluation import evaluate
from wamprobe.reporting import write_reports


def run(output: Path, *, contexts: int, seed: int) -> tuple[Path, Path, Path]:
    """Evaluate the starter adapter and write WAMProbe's standard artifacts."""

    benchmark = PointMass2D()
    suite = benchmark.make_suite(contexts=contexts, seed=seed)
    adapter = StarterWAMAdapter(LinearStateBackend())
    result = evaluate(adapter, benchmark, suite, seed=seed)
    return write_reports(
        output,
        benchmark=benchmark.benchmark_id,
        results=[result],
        seed=seed,
    )


def main() -> None:
    """Parse CLI arguments and run the starter evaluation."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("runs/custom-adapter"))
    parser.add_argument("--contexts", type=int, default=8)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()
    paths = run(args.output, contexts=args.contexts, seed=args.seed)
    for path in paths:
        print(path)


if __name__ == "__main__":
    main()
