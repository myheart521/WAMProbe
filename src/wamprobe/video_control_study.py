"""Toy counterexample study contrasting RGB fidelity with control-value metrics."""

from __future__ import annotations

import json
import math
from collections.abc import Callable
from dataclasses import asdict, dataclass
from itertools import combinations
from pathlib import Path

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
from wamprobe.api.robotics import RGBFrame
from wamprobe.benchmarks.blockpush import BlockPush2D
from wamprobe.benchmarks.gripper_catch import GripperCatch
from wamprobe.manipulation_evaluation import evaluate_manipulation
from wamprobe.video_metrics import invert_rgb, rgb_global_ssim, rgb_psnr


@dataclass(frozen=True, slots=True)
class VideoControlProfile:
    """Model-level traditional video and control metrics."""

    model_id: str
    video_transform: str
    samples: int
    mean_psnr_db: float
    mean_global_ssim: float
    state_fde: float
    candidate_ranking_spearman: float
    top1_regret: float


@dataclass(frozen=True, slots=True)
class VideoControlBenchmarkResult:
    """One benchmark's profiles and cross-profile associations."""

    benchmark_id: str
    profiles: tuple[VideoControlProfile, ...]
    correlations: dict[str, float | None]
    psnr_regret_order_disagreements: int
    comparable_profile_pairs: int


@dataclass(frozen=True, slots=True)
class VideoControlStudy:
    """Multi-benchmark diagnostic counterexample report."""

    benchmarks: tuple[VideoControlBenchmarkResult, ...]
    contexts_per_benchmark: int
    seed: int
    interpretation: str
    schema_version: str = "0.1"

    def to_dict(self) -> dict[str, object]:
        """Return a stable JSON-compatible study."""

        return {
            "schema_version": self.schema_version,
            "contexts_per_benchmark": self.contexts_per_benchmark,
            "seed": self.seed,
            "benchmarks": [asdict(result) for result in self.benchmarks],
            "interpretation": self.interpretation,
        }


@dataclass(frozen=True, slots=True)
class _ProfileSpec:
    model_id: str
    adapter: Callable[[], ManipulationAdapter]
    video_transform: str = "identity"


def _mean(values: list[float]) -> float:
    return sum(values) / len(values)


def _pearson(left: list[float], right: list[float]) -> float | None:
    left_mean = _mean(left)
    right_mean = _mean(right)
    left_centered = [value - left_mean for value in left]
    right_centered = [value - right_mean for value in right]
    denominator = math.sqrt(
        sum(value * value for value in left_centered)
        * sum(value * value for value in right_centered)
    )
    if denominator <= 1e-15:
        return None
    return (
        sum(
            left_value * right_value
            for left_value, right_value in zip(left_centered, right_centered, strict=True)
        )
        / denominator
    )


def _render_frame(
    benchmark: ManipulationBenchmark,
    group_context: object,
    state: object,
) -> RGBFrame:
    # Runtime protocols know the concrete manipulation types, while keeping this helper
    # intentionally small avoids imposing a rendering method on every future benchmark.
    observation = benchmark.observe(group_context, state)  # type: ignore[arg-type]
    if len(observation.frames) != 1:
        raise ValueError("toy video study expects exactly one rendered RGB camera")
    return observation.frames[0]


def _video_fidelity(
    adapter: ManipulationAdapter,
    benchmark: ManipulationBenchmark,
    suite: ManipulationInterventionSuite,
    *,
    seed: int,
    transform: str,
) -> tuple[float, float, int]:
    psnr_values: list[float] = []
    ssim_values: list[float] = []
    try:
        for group in suite.groups:
            for action in group.actions:
                truth = benchmark.rollout(group.context, action)
                predicted = adapter.predict_future(
                    group.context,
                    action,
                    horizon=benchmark.horizon,
                    seed=seed,
                )
                for predicted_state, truth_state in zip(
                    predicted.states,
                    truth.states,
                    strict=True,
                ):
                    predicted_frame = _render_frame(benchmark, group.context, predicted_state)
                    if transform == "invert-rgb":
                        predicted_frame = invert_rgb(predicted_frame)
                    truth_frame = _render_frame(benchmark, group.context, truth_state)
                    psnr_values.append(rgb_psnr(predicted_frame, truth_frame))
                    ssim_values.append(rgb_global_ssim(predicted_frame, truth_frame))
    finally:
        adapter.close()
    return _mean(psnr_values), _mean(ssim_values), len(psnr_values)


def _profile_specs(benchmark: ManipulationBenchmark) -> tuple[_ProfileSpec, ...]:
    return (
        _ProfileSpec("oracle-simulator", lambda: OracleManipulationAdapter(benchmark)),
        _ProfileSpec(
            "appearance-corrupted-oracle",
            lambda: OracleManipulationAdapter(benchmark),
            "invert-rgb",
        ),
        _ProfileSpec("noisy-dynamics", lambda: NoisyManipulationAdapter(benchmark)),
        _ProfileSpec("copy-last-frame", CopyLastManipulationAdapter),
        _ProfileSpec(
            "wrong-direction",
            lambda: WrongDirectionManipulationAdapter(benchmark),
        ),
        _ProfileSpec(
            "action-agnostic",
            lambda: ActionAgnosticManipulationAdapter(benchmark),
        ),
    )


def _run_benchmark(
    benchmark: ManipulationBenchmark,
    *,
    contexts: int,
    seed: int,
) -> VideoControlBenchmarkResult:
    suite = benchmark.make_suite(contexts=contexts, seed=seed)
    profiles: list[VideoControlProfile] = []
    for spec in _profile_specs(benchmark):
        control = evaluate_manipulation(spec.adapter(), benchmark, suite, seed=seed)
        psnr, ssim, samples = _video_fidelity(
            spec.adapter(),
            benchmark,
            suite,
            seed=seed,
            transform=spec.video_transform,
        )
        profiles.append(
            VideoControlProfile(
                model_id=spec.model_id,
                video_transform=spec.video_transform,
                samples=samples,
                mean_psnr_db=psnr,
                mean_global_ssim=ssim,
                state_fde=control.metrics["state_fde"],
                candidate_ranking_spearman=control.metrics["candidate_ranking_spearman"],
                top1_regret=control.metrics["top1_regret"],
            )
        )
    disagreements = 0
    comparable_pairs = 0
    for left, right in combinations(profiles, 2):
        regret_difference = left.top1_regret - right.top1_regret
        psnr_difference = left.mean_psnr_db - right.mean_psnr_db
        if abs(regret_difference) <= 1e-12 or abs(psnr_difference) <= 1e-12:
            continue
        comparable_pairs += 1
        # Lower regret and higher PSNR agree only when their differences have opposite signs.
        if regret_difference * psnr_difference > 0:
            disagreements += 1
    return VideoControlBenchmarkResult(
        benchmark_id=benchmark.benchmark_id,
        profiles=tuple(profiles),
        correlations={
            "psnr_vs_top1_regret_pearson": _pearson(
                [profile.mean_psnr_db for profile in profiles],
                [profile.top1_regret for profile in profiles],
            ),
            "global_ssim_vs_top1_regret_pearson": _pearson(
                [profile.mean_global_ssim for profile in profiles],
                [profile.top1_regret for profile in profiles],
            ),
            "psnr_vs_crc_spearman_pearson": _pearson(
                [profile.mean_psnr_db for profile in profiles],
                [profile.candidate_ranking_spearman for profile in profiles],
            ),
        },
        psnr_regret_order_disagreements=disagreements,
        comparable_profile_pairs=comparable_pairs,
    )


def run_video_control_study(
    *,
    benchmark_names: tuple[str, ...] = ("blockpush", "gripper-catch"),
    contexts: int = 12,
    seed: int = 7,
) -> VideoControlStudy:
    """Run the diagnostic study on deterministic rendered manipulation benchmarks."""

    if contexts <= 0:
        raise ValueError("contexts must be positive")
    benchmarks: list[ManipulationBenchmark] = []
    for name in benchmark_names:
        if name == "blockpush":
            benchmarks.append(BlockPush2D())
        elif name == "gripper-catch":
            benchmarks.append(GripperCatch())
        else:
            raise ValueError(f"unsupported video-control benchmark: {name}")
    if len(benchmarks) != len({benchmark.benchmark_id for benchmark in benchmarks}):
        raise ValueError("video-control benchmark names must be unique")
    return VideoControlStudy(
        benchmarks=tuple(
            _run_benchmark(benchmark, contexts=contexts, seed=seed) for benchmark in benchmarks
        ),
        contexts_per_benchmark=contexts,
        seed=seed,
        interpretation=(
            "The appearance-corrupted oracle preserves exact state/control predictions while "
            "deliberately lowering RGB fidelity. It is a metric counterexample, not a model "
            "quality claim: PSNR/global SSIM cannot replace CRC, regret, or state metrics."
        ),
    )


def render_video_control_markdown(study: VideoControlStudy) -> str:
    """Render a human-readable comparison without a composite score."""

    lines = [
        "# Traditional video fidelity versus control value",
        "",
        study.interpretation,
        "",
    ]
    for benchmark in study.benchmarks:
        lines.extend(
            [
                f"## {benchmark.benchmark_id}",
                "",
                "| Profile | Transform | PSNR dB | Global SSIM | State FDE | CRC | Regret |",
                "|---|---|---:|---:|---:|---:|---:|",
            ]
        )
        for profile in benchmark.profiles:
            lines.append(
                f"| {profile.model_id} | {profile.video_transform} | "
                f"{profile.mean_psnr_db:.4f} | {profile.mean_global_ssim:.4f} | "
                f"{profile.state_fde:.4f} | {profile.candidate_ranking_spearman:.4f} | "
                f"{profile.top1_regret:.4f} |"
            )
        lines.extend(
            [
                "",
                f"PSNR/regret ordering disagreed on "
                f"{benchmark.psnr_regret_order_disagreements}/"
                f"{benchmark.comparable_profile_pairs} comparable profile pairs.",
                "",
            ]
        )
    lines.extend(
        [
            "Global SSIM here is an explicitly labeled whole-frame diagnostic, not the",
            "standard windowed implementation. Exact PSNR matches use a finite 100 dB cap.",
            "",
        ]
    )
    return "\n".join(lines)


def write_video_control_study(output_dir: Path, study: VideoControlStudy) -> tuple[Path, Path]:
    """Write deterministic JSON and Markdown study reports."""

    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "video-control-study.json"
    markdown_path = output_dir / "video-control-study.md"
    json_path.write_text(
        json.dumps(study.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    markdown_path.write_text(render_video_control_markdown(study), encoding="utf-8")
    return json_path, markdown_path
