"""Dependency-free minimal closed-loop replanning study."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Callable
from dataclasses import asdict, dataclass
from itertools import combinations
from pathlib import Path
from random import Random

from wamprobe.adapters.manipulation import (
    ActionAgnosticManipulationAdapter,
    CopyLastManipulationAdapter,
    NoisyManipulationAdapter,
    OracleManipulationAdapter,
    WrongDirectionManipulationAdapter,
)
from wamprobe.api.manipulation import (
    ManipulationAction,
    ManipulationAdapter,
    ManipulationBenchmark,
    ManipulationContext,
    ManipulationInterventionSuite,
    ManipulationState,
    ManipulationTrajectory,
)
from wamprobe.benchmarks.blockpush import BlockPush2D
from wamprobe.benchmarks.gripper_catch import GripperCatch
from wamprobe.manipulation_evaluation import evaluate_manipulation
from wamprobe.stats import MetricSummary, summarize


@dataclass(frozen=True, slots=True)
class ClosedLoopEpisode:
    """One shared-context episode after repeated score-execute-observe cycles."""

    context_id: str
    selected_actions: tuple[str, ...]
    executed_steps: int
    final_return: float
    simulator_oracle_return: float
    oracle_gap: float
    success: bool


@dataclass(frozen=True, slots=True)
class ClosedLoopProfile:
    """Offline and closed-loop measurements for one controller."""

    controller_id: str
    controller_kind: str
    offline_crc_spearman: float | None
    offline_top1_regret: float | None
    return_summary: MetricSummary
    success_summary: MetricSummary
    oracle_gap_summary: MetricSummary
    episodes: tuple[ClosedLoopEpisode, ...]


@dataclass(frozen=True, slots=True)
class ClosedLoopBenchmarkResult:
    """Matched controller results for one analytic benchmark."""

    benchmark_id: str
    control_steps: int
    execute_prefix: int
    profiles: tuple[ClosedLoopProfile, ...]
    correlations: dict[str, float | None]
    offline_return_order_disagreements: int
    comparable_future_scorer_pairs: int


@dataclass(frozen=True, slots=True)
class ClosedLoopStudy:
    """Multi-benchmark closed-loop utility report."""

    benchmarks: tuple[ClosedLoopBenchmarkResult, ...]
    contexts_per_benchmark: int
    seed: int
    resamples: int
    interpretation: str
    schema_version: str = "0.1"

    def to_dict(self) -> dict[str, object]:
        """Return a deterministic JSON-compatible representation."""

        return {
            "schema_version": self.schema_version,
            "contexts_per_benchmark": self.contexts_per_benchmark,
            "seed": self.seed,
            "resamples": self.resamples,
            "benchmarks": [asdict(result) for result in self.benchmarks],
            "interpretation": self.interpretation,
        }


@dataclass(frozen=True, slots=True)
class _AdapterSpec:
    controller_id: str
    adapter: Callable[[], ManipulationAdapter]


@dataclass(frozen=True, slots=True)
class _EpisodeOutcome:
    context_id: str
    selected_actions: tuple[str, ...]
    executed_steps: int
    final_return: float


Selector = Callable[
    [ManipulationContext, tuple[ManipulationAction, ...], int, int],
    ManipulationAction,
]


def _stable_seed(seed: int, *parts: object) -> int:
    material = "\0".join((str(seed), *(str(part) for part in parts))).encode()
    return int.from_bytes(hashlib.sha256(material).digest()[:8], "big")


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


def _adapter_specs(benchmark: ManipulationBenchmark) -> tuple[_AdapterSpec, ...]:
    return (
        _AdapterSpec("oracle-simulator", lambda: OracleManipulationAdapter(benchmark)),
        _AdapterSpec("noisy-dynamics", lambda: NoisyManipulationAdapter(benchmark)),
        _AdapterSpec("copy-last-frame", CopyLastManipulationAdapter),
        _AdapterSpec(
            "wrong-direction",
            lambda: WrongDirectionManipulationAdapter(benchmark),
        ),
        _AdapterSpec(
            "action-agnostic",
            lambda: ActionAgnosticManipulationAdapter(benchmark),
        ),
    )


def _select_predicted_future(
    adapter: ManipulationAdapter,
    benchmark: ManipulationBenchmark,
    context: ManipulationContext,
    actions: tuple[ManipulationAction, ...],
    *,
    seed: int,
    score_steps: int,
) -> ManipulationAction:
    scores: dict[str, float] = {}
    for action in actions:
        predicted = adapter.predict_future(
            context,
            action,
            horizon=benchmark.horizon,
            seed=seed,
        )
        if predicted.context_id != context.context_id:
            raise ValueError("adapter returned a mismatched closed-loop context_id")
        if predicted.action_name != action.name:
            raise ValueError("adapter returned a mismatched closed-loop action_name")
        if len(predicted.states) != benchmark.horizon:
            raise ValueError("adapter returned a mismatched closed-loop horizon")
        scored_prefix = ManipulationTrajectory(
            context_id=context.context_id,
            action_name=action.name,
            states=predicted.states[:score_steps],
        )
        scores[action.name] = benchmark.score(context, scored_prefix)
    return max(actions, key=lambda action: scores[action.name])


def _select_simulator_future(
    benchmark: ManipulationBenchmark,
    context: ManipulationContext,
    actions: tuple[ManipulationAction, ...],
    score_steps: int,
) -> ManipulationAction:
    scores: dict[str, float] = {}
    for action in actions:
        truth = benchmark.rollout(context, action)
        scored_prefix = ManipulationTrajectory(
            context_id=context.context_id,
            action_name=action.name,
            states=truth.states[:score_steps],
        )
        scores[action.name] = benchmark.score(context, scored_prefix)
    return max(actions, key=lambda action: scores[action.name])


def _execute_episode(
    benchmark: ManipulationBenchmark,
    context: ManipulationContext,
    *,
    control_steps: int,
    execute_prefix: int,
    selector: Selector,
) -> _EpisodeOutcome:
    state: ManipulationState = context.initial_state
    states: list[ManipulationState] = []
    selected_actions: list[str] = []
    actions = benchmark.actions()
    remaining = control_steps
    replan_index = 0
    while remaining:
        step_context = ManipulationContext(
            context_id=f"{context.context_id}/replan-{replan_index:04d}",
            initial_state=state,
            goal=context.goal,
        )
        score_steps = min(benchmark.horizon, remaining)
        selected = selector(step_context, actions, replan_index, score_steps)
        if selected not in actions:
            raise ValueError("closed-loop selector returned an unknown action")
        truth = benchmark.rollout(step_context, selected)
        prefix = min(execute_prefix, remaining)
        states.extend(truth.states[:prefix])
        state = truth.states[prefix - 1]
        selected_actions.append(selected.name)
        remaining -= prefix
        replan_index += 1
    trajectory = ManipulationTrajectory(
        context_id=context.context_id,
        action_name="closed-loop",
        states=tuple(states),
    )
    return _EpisodeOutcome(
        context_id=context.context_id,
        selected_actions=tuple(selected_actions),
        executed_steps=len(states),
        final_return=benchmark.score(context, trajectory),
    )


def _episodes_with_oracle(
    outcomes: list[_EpisodeOutcome],
    oracle_returns: dict[str, float],
) -> tuple[ClosedLoopEpisode, ...]:
    episodes: list[ClosedLoopEpisode] = []
    for outcome in outcomes:
        oracle_return = oracle_returns[outcome.context_id]
        gap = oracle_return - outcome.final_return
        episodes.append(
            ClosedLoopEpisode(
                context_id=outcome.context_id,
                selected_actions=outcome.selected_actions,
                executed_steps=outcome.executed_steps,
                final_return=outcome.final_return,
                simulator_oracle_return=oracle_return,
                oracle_gap=gap,
                success=gap <= 1e-9,
            )
        )
    return tuple(episodes)


def _profile(
    *,
    controller_id: str,
    controller_kind: str,
    offline_crc: float | None,
    offline_regret: float | None,
    outcomes: list[_EpisodeOutcome],
    oracle_returns: dict[str, float],
    resamples: int,
    seed: int,
) -> ClosedLoopProfile:
    episodes = _episodes_with_oracle(outcomes, oracle_returns)
    return ClosedLoopProfile(
        controller_id=controller_id,
        controller_kind=controller_kind,
        offline_crc_spearman=offline_crc,
        offline_top1_regret=offline_regret,
        return_summary=summarize(
            [episode.final_return for episode in episodes],
            resamples=resamples,
            seed=_stable_seed(seed, controller_id, "return"),
        ),
        success_summary=summarize(
            [float(episode.success) for episode in episodes],
            resamples=resamples,
            seed=_stable_seed(seed, controller_id, "success"),
        ),
        oracle_gap_summary=summarize(
            [episode.oracle_gap for episode in episodes],
            resamples=resamples,
            seed=_stable_seed(seed, controller_id, "oracle-gap"),
        ),
        episodes=episodes,
    )


def _run_benchmark(
    benchmark: ManipulationBenchmark,
    *,
    contexts: int,
    seed: int,
    control_steps: int,
    execute_prefix: int,
    resamples: int,
) -> ClosedLoopBenchmarkResult:
    suite: ManipulationInterventionSuite = benchmark.make_suite(contexts=contexts, seed=seed)
    simulator_outcomes = [
        _execute_episode(
            benchmark,
            group.context,
            control_steps=control_steps,
            execute_prefix=execute_prefix,
            selector=lambda current, actions, _index, score_steps: _select_simulator_future(
                benchmark,
                current,
                actions,
                score_steps,
            ),
        )
        for group in suite.groups
    ]
    oracle_returns = {outcome.context_id: outcome.final_return for outcome in simulator_outcomes}

    profiles: list[ClosedLoopProfile] = []
    for spec in _adapter_specs(benchmark):
        offline = evaluate_manipulation(spec.adapter(), benchmark, suite, seed=seed)
        adapter = spec.adapter()
        try:

            def predicted_selector(
                current: ManipulationContext,
                actions: tuple[ManipulationAction, ...],
                _index: int,
                score_steps: int,
                current_adapter: ManipulationAdapter = adapter,
            ) -> ManipulationAction:
                return _select_predicted_future(
                    current_adapter,
                    benchmark,
                    current,
                    actions,
                    seed=seed,
                    score_steps=score_steps,
                )

            outcomes = [
                _execute_episode(
                    benchmark,
                    group.context,
                    control_steps=control_steps,
                    execute_prefix=execute_prefix,
                    selector=predicted_selector,
                )
                for group in suite.groups
            ]
        finally:
            adapter.close()
        profiles.append(
            _profile(
                controller_id=spec.controller_id,
                controller_kind="future-scorer",
                offline_crc=offline.metrics["candidate_ranking_spearman"],
                offline_regret=offline.metrics["top1_regret"],
                outcomes=outcomes,
                oracle_returns=oracle_returns,
                resamples=resamples,
                seed=seed,
            )
        )

    profiles.append(
        _profile(
            controller_id="simulator-oracle-scorer",
            controller_kind="simulator-control",
            offline_crc=None,
            offline_regret=None,
            outcomes=simulator_outcomes,
            oracle_returns=oracle_returns,
            resamples=resamples,
            seed=seed,
        )
    )
    fixed_outcomes: list[_EpisodeOutcome] = []
    random_outcomes: list[_EpisodeOutcome] = []
    for group in suite.groups:
        fixed_action = benchmark.optimal_action(group.context)

        def fixed_selector(
            _current: ManipulationContext,
            _actions: tuple[ManipulationAction, ...],
            _index: int,
            _score_steps: int,
            action: ManipulationAction = fixed_action,
        ) -> ManipulationAction:
            return action

        fixed_outcomes.append(
            _execute_episode(
                benchmark,
                group.context,
                control_steps=control_steps,
                execute_prefix=execute_prefix,
                selector=fixed_selector,
            )
        )

        def random_selector(
            current: ManipulationContext,
            actions: tuple[ManipulationAction, ...],
            index: int,
            _score_steps: int,
        ) -> ManipulationAction:
            rng = Random(_stable_seed(seed, current.context_id, index, "random-controller"))
            return actions[rng.randrange(len(actions))]

        random_outcomes.append(
            _execute_episode(
                benchmark,
                group.context,
                control_steps=control_steps,
                execute_prefix=execute_prefix,
                selector=random_selector,
            )
        )
    profiles.extend(
        (
            _profile(
                controller_id="fixed-action-policy",
                controller_kind="action-only-control",
                offline_crc=None,
                offline_regret=None,
                outcomes=fixed_outcomes,
                oracle_returns=oracle_returns,
                resamples=resamples,
                seed=seed,
            ),
            _profile(
                controller_id="random-candidate",
                controller_kind="random-control",
                offline_crc=None,
                offline_regret=None,
                outcomes=random_outcomes,
                oracle_returns=oracle_returns,
                resamples=resamples,
                seed=seed,
            ),
        )
    )

    future_profiles = [
        profile for profile in profiles if profile.controller_kind == "future-scorer"
    ]
    disagreements = 0
    comparable = 0
    for left, right in combinations(future_profiles, 2):
        assert left.offline_crc_spearman is not None
        assert right.offline_crc_spearman is not None
        offline_difference = left.offline_crc_spearman - right.offline_crc_spearman
        return_difference = left.return_summary.mean - right.return_summary.mean
        if abs(offline_difference) <= 1e-12 or abs(return_difference) <= 1e-12:
            continue
        comparable += 1
        if offline_difference * return_difference < 0:
            disagreements += 1
    return ClosedLoopBenchmarkResult(
        benchmark_id=benchmark.benchmark_id,
        control_steps=control_steps,
        execute_prefix=execute_prefix,
        profiles=tuple(profiles),
        correlations={
            "offline_crc_vs_closed_loop_return_pearson": _pearson(
                [
                    profile.offline_crc_spearman
                    for profile in future_profiles
                    if profile.offline_crc_spearman is not None
                ],
                [profile.return_summary.mean for profile in future_profiles],
            ),
            "offline_regret_vs_closed_loop_return_pearson": _pearson(
                [
                    profile.offline_top1_regret
                    for profile in future_profiles
                    if profile.offline_top1_regret is not None
                ],
                [profile.return_summary.mean for profile in future_profiles],
            ),
        },
        offline_return_order_disagreements=disagreements,
        comparable_future_scorer_pairs=comparable,
    )


def run_closed_loop_study(
    *,
    benchmark_names: tuple[str, ...] = ("blockpush", "gripper-catch"),
    contexts: int = 12,
    seed: int = 7,
    control_steps: int | None = None,
    execute_prefix: int = 1,
    resamples: int = 1000,
) -> ClosedLoopStudy:
    """Run score-execute-observe replanning on deterministic manipulation tasks."""

    if contexts <= 0:
        raise ValueError("contexts must be positive")
    if control_steps is not None and control_steps <= 0:
        raise ValueError("control_steps must be positive")
    if execute_prefix <= 0:
        raise ValueError("execute_prefix must be positive")
    if resamples <= 0:
        raise ValueError("resamples must be positive")
    if not benchmark_names:
        raise ValueError("at least one closed-loop benchmark is required")

    benchmarks: list[ManipulationBenchmark] = []
    for name in benchmark_names:
        if name == "blockpush":
            benchmarks.append(BlockPush2D())
        elif name == "gripper-catch":
            benchmarks.append(GripperCatch())
        else:
            raise ValueError(f"unsupported closed-loop benchmark: {name}")
    if len(benchmarks) != len({benchmark.benchmark_id for benchmark in benchmarks}):
        raise ValueError("closed-loop benchmark names must be unique")
    for benchmark in benchmarks:
        if execute_prefix > benchmark.horizon:
            raise ValueError("execute_prefix must not exceed the prediction horizon")

    return ClosedLoopStudy(
        benchmarks=tuple(
            _run_benchmark(
                benchmark,
                contexts=contexts,
                seed=seed,
                control_steps=benchmark.horizon if control_steps is None else control_steps,
                execute_prefix=execute_prefix,
                resamples=resamples,
            )
            for benchmark in benchmarks
        ),
        contexts_per_benchmark=contexts,
        seed=seed,
        resamples=resamples,
        interpretation=(
            "Each cycle scores the same legal action set, executes only the selected "
            "trajectory prefix in true dynamics, then replans from the resulting state; "
            "the scoring window is capped by the remaining episode budget. "
            "Cross-profile Pearson values are descriptive because there are only five "
            "future scorers; context-block intervals remain the primary uncertainty view."
        ),
    )


def _format_optional(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.4f}"


def render_closed_loop_markdown(study: ClosedLoopStudy) -> str:
    """Render closed-loop results without a composite score."""

    lines = ["# Minimal closed-loop replanning utility", "", study.interpretation, ""]
    for benchmark in study.benchmarks:
        lines.extend(
            [
                f"## {benchmark.benchmark_id}",
                "",
                f"Control steps: {benchmark.control_steps}; execute prefix: "
                f"{benchmark.execute_prefix}.",
                "",
                "| Controller | Kind | Offline CRC | Offline regret | "
                "Closed return [95% CI] | Success | Oracle gap |",
                "|---|---|---:|---:|---:|---:|---:|",
            ]
        )
        for profile in benchmark.profiles:
            interval = profile.return_summary.confidence_interval
            lines.append(
                f"| {profile.controller_id} | {profile.controller_kind} | "
                f"{_format_optional(profile.offline_crc_spearman)} | "
                f"{_format_optional(profile.offline_top1_regret)} | "
                f"{profile.return_summary.mean:.4f} "
                f"[{interval.lower:.4f}, {interval.upper:.4f}] | "
                f"{profile.success_summary.mean:.4f} | "
                f"{profile.oracle_gap_summary.mean:.4f} |"
            )
        crc_correlation = benchmark.correlations["offline_crc_vs_closed_loop_return_pearson"]
        regret_correlation = benchmark.correlations["offline_regret_vs_closed_loop_return_pearson"]
        lines.extend(
            [
                "",
                "Future-scorer profile correlation: offline CRC vs closed-loop return = "
                f"{_format_optional(crc_correlation)}; offline regret vs closed-loop "
                f"return = {_format_optional(regret_correlation)}.",
                "",
                "Offline-CRC/return ordering disagreed on "
                f"{benchmark.offline_return_order_disagreements}/"
                f"{benchmark.comparable_future_scorer_pairs} comparable future-scorer pairs.",
                "",
            ]
        )
    lines.extend(
        [
            "Success means matching the greedy simulator-future scorer's final return within",
            "1e-9 on the same context and control budget. Score ties use the benchmark's stable",
            "candidate order. The scoring horizon is capped by the episode steps remaining,",
            "preventing terminal scores beyond the execution budget. These analytic tasks",
            "validate the evaluator; they do not establish real-robot or large-model closed-loop",
            "performance.",
            "",
        ]
    )
    return "\n".join(lines)


def write_closed_loop_study(output_dir: Path, study: ClosedLoopStudy) -> tuple[Path, Path]:
    """Write deterministic JSON and Markdown closed-loop reports."""

    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "closed-loop-study.json"
    markdown_path = output_dir / "closed-loop-study.md"
    json_path.write_text(
        json.dumps(study.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    markdown_path.write_text(render_closed_loop_markdown(study), encoding="utf-8")
    return json_path, markdown_path
